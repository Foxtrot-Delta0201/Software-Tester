-- =============================================================================
-- Foci-Med Core — Database Initialization Script (PostgreSQL 16)
-- -----------------------------------------------------------------------------
-- Executed once by the postgres Docker entrypoint against 'focimed_core'.
-- Establishes multi-tenant schemas and enforces tenant data isolation via
-- Row-Level Security (RLS), satisfying POPIA / HIPAA segregation requirements.
--
-- Design notes:
--   * The superuser (postgres) BYPASSES RLS by design — it is used only for
--     administration and seeding. All tenant-scoped access must occur through
--     the non-superuser 'app_user' role, which is fully subject to RLS.
--   * FORCE ROW LEVEL SECURITY additionally subjects the *table owner* to the
--     policy, closing the owner-bypass gap.
--   * Isolation key: the per-session GUC 'app.current_tenant'. When unset, the
--     strict current_setting() call raises an error -> access is denied by
--     default (fail-closed), never silently granted.
-- =============================================================================

-- Wrap the entire bootstrap in a single transaction for all-or-nothing safety.
BEGIN;

-- -----------------------------------------------------------------------------
-- 0. Extensions
-- -----------------------------------------------------------------------------
-- gen_random_uuid() ships with pgcrypto; guarantee availability across images.
CREATE EXTENSION IF NOT EXISTS pgcrypto;

-- -----------------------------------------------------------------------------
-- 1. Schemas
-- -----------------------------------------------------------------------------
-- 'public' is the master system schema (created by initdb); declare explicitly
-- for clarity and idempotency.
CREATE SCHEMA IF NOT EXISTS public;

-- 'pool_01' is a tenant pool schema holding co-located tenant data that is
-- logically separated at the row level by RLS.
CREATE SCHEMA IF NOT EXISTS pool_01;

-- -----------------------------------------------------------------------------
-- 2. Application role (non-superuser) — the identity used by the QA harness
-- -----------------------------------------------------------------------------
-- Created idempotently. This role is intentionally NOT a superuser so that RLS
-- policies actually apply to it. Password is overridable for local sandboxes.
DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'app_user') THEN
        CREATE ROLE app_user LOGIN PASSWORD 'app_user_local_secret';
    END IF;
END
$$;

-- Allow the application role to reach the tenant pool schema.
GRANT USAGE ON SCHEMA pool_01 TO app_user;

-- -----------------------------------------------------------------------------
-- 3. Tables
-- -----------------------------------------------------------------------------

-- 3a. Tenants — one row per medical practice in this pool.
CREATE TABLE IF NOT EXISTS pool_01.tenants (
    tenant_id     UUID         PRIMARY KEY DEFAULT gen_random_uuid(),
    practice_name VARCHAR(255) NOT NULL,
    created_at    TIMESTAMPTZ  NOT NULL DEFAULT now()
);

-- 3b. Patients — PHI rows, isolated per tenant via RLS below.
CREATE TABLE IF NOT EXISTS pool_01.patients (
    patient_id        UUID         PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id         UUID         NOT NULL
        REFERENCES pool_01.tenants (tenant_id) ON DELETE CASCADE,
    first_name        VARCHAR(255) NOT NULL,
    last_name         VARCHAR(255) NOT NULL,
    medical_aid_number VARCHAR(64) NOT NULL
);

-- Supporting index for the tenant predicate used by the RLS policy.
CREATE INDEX IF NOT EXISTS idx_patients_tenant_id
    ON pool_01.patients (tenant_id);

-- Table-level privileges for the application role (DML only; no DDL).
GRANT SELECT, INSERT, UPDATE, DELETE ON pool_01.patients TO app_user;
GRANT SELECT, INSERT, UPDATE, DELETE ON pool_01.tenants  TO app_user;

-- -----------------------------------------------------------------------------
-- 4. Row-Level Security on pool_01.patients
-- -----------------------------------------------------------------------------
-- ENABLE  -> policies are consulted for non-owner roles (e.g. app_user).
-- FORCE   -> policies are ALSO enforced against the table owner, eliminating
--            the owner-bypass loophole. (Superusers still bypass — never run
--            tenant queries as a superuser.)
ALTER TABLE pool_01.patients ENABLE  ROW LEVEL SECURITY;
ALTER TABLE pool_01.patients FORCE   ROW LEVEL SECURITY;

-- Drop-then-create keeps this script re-runnable without duplicate-policy errors.
DROP POLICY IF EXISTS tenant_isolation_policy ON pool_01.patients;

-- Tenant isolation: a session may only see/affect rows whose tenant_id matches
-- the UUID stored in the 'app.current_tenant' GUC for that session.
--
--   * USING        -> filters rows visible to SELECT/UPDATE/DELETE.
--   * WITH CHECK    -> prevents INSERT/UPDATE from writing rows belonging to a
--                      different tenant (no cross-tenant data injection).
--   * current_setting(..., FALSE) is STRICT: if 'app.current_tenant' is unset,
--     it raises 'unrecognized configuration parameter' -> fail-closed.
CREATE POLICY tenant_isolation_policy
    ON pool_01.patients
    FOR ALL
    USING      (tenant_id = current_setting('app.current_tenant', false)::uuid)
    WITH CHECK (tenant_id = current_setting('app.current_tenant', false)::uuid);

-- =============================================================================
-- SUITE B — Temporal Time-Travel (SCD Type 2 tariff history)
-- =============================================================================

-- 5a. Standard SA tariff codes with full effective-dated history.
--     Each price change closes the prior row (effective_to + is_current=false)
--     and opens a new row, giving point-in-time ("time-travel") pricing.
CREATE TABLE IF NOT EXISTS public.sys_tariffs (
    tariff_id      UUID         PRIMARY KEY DEFAULT gen_random_uuid(),
    tariff_code    VARCHAR(16)  NOT NULL,             -- e.g. '0101' = Consultation
    base_price     DECIMAL(12,2) NOT NULL CHECK (base_price >= 0),
    effective_from TIMESTAMPTZ  NOT NULL,
    effective_to   TIMESTAMPTZ,                       -- NULL = open-ended / current
    is_current     BOOLEAN      NOT NULL DEFAULT true,
    -- A version is well-formed only if it is open-ended or ends after it starts.
    CONSTRAINT chk_tariff_interval
        CHECK (effective_to IS NULL OR effective_to > effective_from)
);

-- Fast point-in-time lookups by code over the validity interval.
CREATE INDEX IF NOT EXISTS idx_sys_tariffs_code_window
    ON public.sys_tariffs (tariff_code, effective_from, effective_to);

-- Guarantee at most one CURRENT row per tariff_code (data-integrity guard).
CREATE UNIQUE INDEX IF NOT EXISTS uq_sys_tariffs_one_current
    ON public.sys_tariffs (tariff_code)
    WHERE is_current;

GRANT SELECT, INSERT, UPDATE, DELETE ON public.sys_tariffs TO app_user;

-- 5b. Point-in-time price resolver.
--     Uses a HALF-OPEN interval [effective_from, effective_to): the lower bound
--     is inclusive, the upper bound exclusive, so adjacent versions never
--     overlap and never leave a gap at the boundary instant.
--     Fail-closed behaviour:
--       * Future-dated service (DoS > now())     -> RAISE (out of range).
--       * No version covers the DoS              -> RAISE no_data_found.
CREATE OR REPLACE FUNCTION public.resolve_tariff_price(
    p_tariff_code VARCHAR,
    p_dos         TIMESTAMPTZ
) RETURNS DECIMAL
LANGUAGE plpgsql
STABLE
AS $$
DECLARE
    v_price DECIMAL(12,2);
BEGIN
    -- Reject claims for services not yet rendered (future-dated DoS).
    IF p_dos > now() THEN
        RAISE EXCEPTION
            'Date of Service % is in the future and out of valid range', p_dos
            USING ERRCODE = 'datetime_field_overflow';   -- SQLSTATE 22008
    END IF;

    SELECT base_price
      INTO v_price
      FROM public.sys_tariffs
     WHERE tariff_code = p_tariff_code
       AND effective_from <= p_dos
       AND (effective_to IS NULL OR p_dos < effective_to)
     LIMIT 1;

    IF NOT FOUND THEN
        RAISE EXCEPTION
            'No tariff version for code % effective on %', p_tariff_code, p_dos
            USING ERRCODE = 'no_data_found';             -- SQLSTATE P0002
    END IF;

    RETURN v_price;
END;
$$;

-- =============================================================================
-- SUITE C — EDI claim state machine + chaos audit
-- =============================================================================

-- 6a. Claim header carrying the workflow status.
CREATE TABLE IF NOT EXISTS pool_01.claim_header (
    claim_id   UUID         PRIMARY KEY DEFAULT gen_random_uuid(),
    status     VARCHAR(16)  NOT NULL DEFAULT 'DRAFT',
    tenant_id  UUID         NOT NULL REFERENCES pool_01.tenants (tenant_id),
    updated_at TIMESTAMPTZ  NOT NULL DEFAULT now(),
    -- Domain guard: only known states may ever be stored.
    CONSTRAINT chk_claim_status CHECK (
        status IN ('DRAFT','VALIDATED','TRANSMITTED','ACKNOWLEDGED','PAID','REJECTED')
    )
);

CREATE INDEX IF NOT EXISTS idx_claim_header_tenant
    ON pool_01.claim_header (tenant_id);

GRANT SELECT, INSERT, UPDATE, DELETE ON pool_01.claim_header TO app_user;

-- 6b. Audit log for REJECTED / illegal transition attempts.
--     Written by the application in an independent transaction (a trigger
--     RAISE rolls back its own transaction, so the log must live outside it).
CREATE TABLE IF NOT EXISTS pool_01.claim_audit_log (
    audit_id     BIGINT       GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    claim_id     UUID,
    from_status  VARCHAR(16),
    to_status    VARCHAR(16),
    outcome      VARCHAR(16)  NOT NULL,   -- 'REJECTED' | 'ERROR'
    detail       TEXT,
    logged_at    TIMESTAMPTZ  NOT NULL DEFAULT now()
);

GRANT SELECT, INSERT ON pool_01.claim_audit_log TO app_user;

-- 6c. State-transition enforcement.
--     A CHECK constraint cannot see the prior row, so a BEFORE UPDATE trigger
--     is used to compare OLD.status -> NEW.status against the legal map:
--       DRAFT -> VALIDATED -> TRANSMITTED -> ACKNOWLEDGED -> PAID | REJECTED
--     Any other change raises an exception (SQLSTATE 23514, check_violation),
--     which the harness records to claim_audit_log out-of-band.
CREATE OR REPLACE FUNCTION pool_01.enforce_claim_transition()
RETURNS TRIGGER
LANGUAGE plpgsql
AS $$
BEGIN
    -- No-op updates (same status) are allowed and skip transition checks.
    IF NEW.status = OLD.status THEN
        NEW.updated_at := now();
        RETURN NEW;
    END IF;

    IF NOT (
        (OLD.status = 'DRAFT'        AND NEW.status = 'VALIDATED')   OR
        (OLD.status = 'VALIDATED'    AND NEW.status = 'TRANSMITTED') OR
        (OLD.status = 'TRANSMITTED'  AND NEW.status = 'ACKNOWLEDGED') OR
        (OLD.status = 'ACKNOWLEDGED' AND NEW.status IN ('PAID','REJECTED'))
    ) THEN
        RAISE EXCEPTION
            'Illegal claim state transition % -> %', OLD.status, NEW.status
            USING ERRCODE = 'check_violation';           -- SQLSTATE 23514
    END IF;

    NEW.updated_at := now();
    RETURN NEW;
END;
$$;

DROP TRIGGER IF EXISTS trg_enforce_claim_transition ON pool_01.claim_header;
CREATE TRIGGER trg_enforce_claim_transition
    BEFORE UPDATE ON pool_01.claim_header
    FOR EACH ROW
    EXECUTE FUNCTION pool_01.enforce_claim_transition();

COMMIT;

-- =============================================================================
-- End of initialization. Database 'focimed_core' is ready for the QA harness.
-- =============================================================================
