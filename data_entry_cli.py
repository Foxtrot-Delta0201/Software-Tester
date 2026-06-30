"""Foci-Med Manual Data Entry CLI.

A terminal-driven CRUD interface for inserting, viewing, editing and
saving records in the local Postgres database without running the full
React frontend.

Usage::

    python data_entry_cli.py

Reads the same .env that the test suites use, so no extra configuration
is needed when the Docker Compose DB is already running.

Supported entities
------------------
  Tenants   — create, list, delete
  Patients  — create, list, search, edit, delete
  Claims    — create, list, advance status, view audit log
"""

from __future__ import annotations

import os
import sys
import uuid
from datetime import date

import psycopg2
import psycopg2.extras
from dotenv import load_dotenv

load_dotenv()

DB_HOST    = os.getenv("FOCIMED_DB_HOST",   "localhost")
DB_PORT    = int(os.getenv("FOCIMED_DB_PORT", "5432"))
DB_NAME    = os.getenv("FOCIMED_DB_NAME",   "focimed_core")
SUPER_USER = os.getenv("FOCIMED_SUPERUSER", "postgres")
SUPER_PASS = os.getenv("POSTGRES_PASSWORD", "focimed_local_secret")

CLAIM_STATUSES = ["DRAFT", "VALIDATED", "TRANSMITTED", "ACKNOWLEDGED", "PAID", "REJECTED"]


# ── Connection ─────────────────────────────────────────────────────────────── #
def _connect() -> psycopg2.extensions.connection:
    return psycopg2.connect(
        host=DB_HOST, port=DB_PORT, dbname=DB_NAME,
        user=SUPER_USER, password=SUPER_PASS,
    )


# ── UI helpers ─────────────────────────────────────────────────────────────── #
def _prompt(label: str, default: str = "") -> str:
    hint = f" [{default}]" if default else ""
    try:
        raw = input(f"  {label}{hint}: ").strip()
    except (EOFError, KeyboardInterrupt):
        print()
        return default
    return raw if raw else default


def _choose(options: list[str]) -> int:
    """Print a numbered menu; return 1-based index or 0 for Back/Cancel."""
    for i, opt in enumerate(options, 1):
        print(f"  [{i}] {opt}")
    print("  [0] Back")
    while True:
        try:
            raw = input("  Choice: ").strip()
        except (EOFError, KeyboardInterrupt):
            return 0
        if raw.isdigit() and 0 <= int(raw) <= len(options):
            return int(raw)
        print(f"  Enter a number between 0 and {len(options)}.")


def _divider(title: str = "") -> None:
    if title:
        print(f"\n── {title} {'─' * max(0, 44 - len(title))}")
    else:
        print("─" * 48)


# ── Tenant helpers ─────────────────────────────────────────────────────────── #
def _list_tenants(cur) -> list[tuple]:
    cur.execute(
        "SELECT tenant_id, practice_name FROM pool_01.tenants ORDER BY practice_name;"
    )
    return cur.fetchall()


def _select_tenant(cur) -> tuple | None:
    rows = _list_tenants(cur)
    if not rows:
        print("  No tenants found — create one first.")
        return None
    print()
    for i, (tid, name) in enumerate(rows, 1):
        print(f"  [{i}] {name}  ({tid})")
    print("  [0] Cancel")
    while True:
        raw = input("  Select tenant: ").strip()
        if raw.isdigit():
            n = int(raw)
            if n == 0:
                return None
            if 1 <= n <= len(rows):
                return rows[n - 1]
        print("  Invalid.")


# ── Tenant menu ────────────────────────────────────────────────────────────── #
def menu_tenants(conn) -> None:
    while True:
        _divider("Tenants")
        choice = _choose(["List tenants", "Create tenant", "Delete tenant"])
        if choice == 0:
            return
        cur = conn.cursor()

        if choice == 1:  # list
            rows = _list_tenants(cur)
            if not rows:
                print("  (no tenants)")
            else:
                print()
                for tid, name in rows:
                    print(f"  {name:<35} {tid}")

        elif choice == 2:  # create
            name = _prompt("Practice name")
            if not name:
                print("  Name required — cancelled.")
                cur.close()
                continue
            new_id = uuid.uuid4()
            cur.execute(
                "INSERT INTO pool_01.tenants (tenant_id, practice_name) VALUES (%s, %s);",
                (str(new_id), name),
            )
            conn.commit()
            print(f"  Saved.  ID: {new_id}")

        elif choice == 3:  # delete
            t = _select_tenant(cur)
            if not t:
                cur.close()
                continue
            tid, name = t
            confirm = _prompt(f'Delete "{name}"? Type YES to confirm')
            if confirm == "YES":
                cur.execute(
                    "DELETE FROM pool_01.tenants WHERE tenant_id = %s;", (str(tid),)
                )
                conn.commit()
                print("  Deleted.")
            else:
                print("  Cancelled.")

        cur.close()


# ── Patient menu ───────────────────────────────────────────────────────────── #
def menu_patients(conn) -> None:
    while True:
        _divider("Patients")
        choice = _choose(
            ["List patients", "Create patient", "Edit patient", "Delete patient"]
        )
        if choice == 0:
            return
        cur = conn.cursor()

        if choice == 1:  # list
            t = _select_tenant(cur)
            if not t:
                cur.close()
                continue
            tid, _ = t
            cur.execute(
                """
                SELECT patient_id, first_name, last_name, date_of_birth, medical_aid_number
                FROM pool_01.patients
                WHERE tenant_id = %s
                ORDER BY last_name, first_name
                LIMIT 50;
                """,
                (str(tid),),
            )
            rows = cur.fetchall()
            print()
            if not rows:
                print("  (no patients for this tenant)")
            else:
                for pid, fn, ln, dob, ma in rows:
                    print(
                        f"  {ln}, {fn:<20}  DOB:{str(dob) if dob else 'n/a':<12}"
                        f"  MA:{ma or 'n/a':<16}  [{pid}]"
                    )
                if len(rows) == 50:
                    print("  (showing first 50 — use search/edit to find others)")

        elif choice == 2:  # create
            t = _select_tenant(cur)
            if not t:
                cur.close()
                continue
            tid, _ = t
            first  = _prompt("First name")
            last   = _prompt("Last name")
            if not first or not last:
                print("  First and last name required — cancelled.")
                cur.close()
                continue
            dob    = _prompt("Date of birth (YYYY-MM-DD)", "")
            ma_num = _prompt("Medical aid number", "")
            pid = uuid.uuid4()
            cur.execute(
                """
                INSERT INTO pool_01.patients
                    (patient_id, tenant_id, first_name, last_name,
                     date_of_birth, medical_aid_number)
                VALUES (%s, %s, %s, %s, %s, %s);
                """,
                (str(pid), str(tid), first, last, dob or None, ma_num or None),
            )
            conn.commit()
            print(f"  Saved patient {pid}")

        elif choice == 3:  # edit
            t = _select_tenant(cur)
            if not t:
                cur.close()
                continue
            tid, _ = t
            search = _prompt("Search by last name (partial, leave blank for all)")
            cur.execute(
                """
                SELECT patient_id, first_name, last_name, date_of_birth, medical_aid_number
                FROM pool_01.patients
                WHERE tenant_id = %s AND last_name ILIKE %s
                ORDER BY last_name, first_name LIMIT 20;
                """,
                (str(tid), f"%{search}%"),
            )
            rows = cur.fetchall()
            if not rows:
                print("  No matches.")
                cur.close()
                continue
            print()
            for i, (pid, fn, ln, dob, ma) in enumerate(rows, 1):
                print(f"  [{i}] {ln}, {fn}  [{pid}]")
            print("  [0] Cancel")
            raw = input("  Select patient to edit: ").strip()
            if not raw.isdigit() or int(raw) == 0 or int(raw) > len(rows):
                cur.close()
                continue
            pid, fn, ln, dob, ma = rows[int(raw) - 1]
            print(f"\n  Editing {fn} {ln} — press Enter to keep the current value.")
            new_first = _prompt("First name", fn)
            new_last  = _prompt("Last name",  ln)
            new_dob   = _prompt("Date of birth", str(dob) if dob else "")
            new_ma    = _prompt("Medical aid number", ma or "")
            cur.execute(
                """
                UPDATE pool_01.patients
                SET first_name = %s, last_name = %s,
                    date_of_birth = %s, medical_aid_number = %s
                WHERE patient_id = %s;
                """,
                (new_first, new_last, new_dob or None, new_ma or None, str(pid)),
            )
            conn.commit()
            print("  Saved.")

        elif choice == 4:  # delete
            t = _select_tenant(cur)
            if not t:
                cur.close()
                continue
            tid, _ = t
            pid_raw = _prompt("Patient UUID to delete")
            try:
                pid = uuid.UUID(pid_raw)
            except ValueError:
                print("  Invalid UUID format.")
                cur.close()
                continue
            cur.execute(
                """
                SELECT first_name, last_name
                FROM pool_01.patients
                WHERE patient_id = %s AND tenant_id = %s;
                """,
                (str(pid), str(tid)),
            )
            row = cur.fetchone()
            if not row:
                print("  Patient not found in this tenant.")
                cur.close()
                continue
            confirm = _prompt(f'Delete {row[0]} {row[1]}? Type YES')
            if confirm == "YES":
                cur.execute(
                    "DELETE FROM pool_01.patients WHERE patient_id = %s;", (str(pid),)
                )
                conn.commit()
                print("  Deleted.")
            else:
                print("  Cancelled.")

        cur.close()


# ── Claims menu ────────────────────────────────────────────────────────────── #
def menu_claims(conn) -> None:
    while True:
        _divider("Claims")
        choice = _choose(
            [
                "List claims",
                "Create DRAFT claim",
                "Advance claim status",
                "View claim audit log",
            ]
        )
        if choice == 0:
            return
        cur = conn.cursor()

        if choice == 1:  # list
            t = _select_tenant(cur)
            if not t:
                cur.close()
                continue
            tid, _ = t
            cur.execute(
                """
                SELECT claim_id, status, created_at
                FROM pool_01.claim_header
                WHERE tenant_id = %s
                ORDER BY created_at DESC LIMIT 30;
                """,
                (str(tid),),
            )
            rows = cur.fetchall()
            print()
            if not rows:
                print("  (no claims)")
            for cid, status, created in rows:
                print(f"  [{status:<15}]  {cid}  created: {created}")

        elif choice == 2:  # create
            t = _select_tenant(cur)
            if not t:
                cur.close()
                continue
            tid, _ = t
            cid = uuid.uuid4()
            cur.execute(
                """
                INSERT INTO pool_01.claim_header (claim_id, status, tenant_id)
                VALUES (%s, 'DRAFT', %s);
                """,
                (str(cid), str(tid)),
            )
            conn.commit()
            print(f"  Created DRAFT claim: {cid}")

        elif choice == 3:  # advance status
            t = _select_tenant(cur)
            if not t:
                cur.close()
                continue
            tid, _ = t
            cid_raw = _prompt("Claim UUID")
            try:
                cid = uuid.UUID(cid_raw)
            except ValueError:
                print("  Invalid UUID.")
                cur.close()
                continue
            cur.execute(
                "SELECT status FROM pool_01.claim_header WHERE claim_id = %s AND tenant_id = %s;",
                (str(cid), str(tid)),
            )
            row = cur.fetchone()
            if not row:
                print("  Claim not found in this tenant.")
                cur.close()
                continue
            print(f"  Current status: {row[0]}")
            print("  Select new status:")
            idx = _choose(CLAIM_STATUSES)
            if idx == 0:
                cur.close()
                continue
            new_status = CLAIM_STATUSES[idx - 1]
            try:
                cur.execute(
                    "UPDATE pool_01.claim_header SET status = %s WHERE claim_id = %s;",
                    (new_status, str(cid)),
                )
                conn.commit()
                print(f"  Status updated to {new_status}")
            except psycopg2.Error as exc:
                conn.rollback()
                print(f"  Rejected by DB: [{exc.pgcode}] {(exc.pgerror or '').strip()}")

        elif choice == 4:  # audit log
            cid_raw = _prompt("Claim UUID")
            try:
                cid = uuid.UUID(cid_raw)
            except ValueError:
                print("  Invalid UUID.")
                cur.close()
                continue
            cur.execute(
                """
                SELECT from_status, to_status, outcome, detail, logged_at
                FROM pool_01.claim_audit_log
                WHERE claim_id = %s
                ORDER BY logged_at;
                """,
                (str(cid),),
            )
            rows = cur.fetchall()
            print()
            if not rows:
                print("  (no audit entries for this claim)")
            for frm, to, outcome, detail, ts in rows:
                print(f"  {ts}  {frm} -> {to}  [{outcome}]  {detail}")

        cur.close()


# ── Main loop ──────────────────────────────────────────────────────────────── #
def main() -> None:
    print("\nFoci-Med Data Entry CLI")
    print(f"Connecting to {DB_NAME}@{DB_HOST}:{DB_PORT} as {SUPER_USER} ...")
    try:
        conn = _connect()
    except psycopg2.OperationalError as exc:
        print(f"\nCannot connect: {exc}")
        print("Make sure Docker Compose is running:  docker compose up -d")
        sys.exit(1)
    print("Connected.\n")

    menus = {
        "1": ("Tenants",  menu_tenants),
        "2": ("Patients", menu_patients),
        "3": ("Claims",   menu_claims),
    }

    while True:
        print("\n════ Foci-Med Data Entry ════")
        for k, (label, _) in menus.items():
            print(f"  [{k}] {label}")
        print("  [0] Exit")
        try:
            raw = input("  Choice: ").strip()
        except (EOFError, KeyboardInterrupt):
            raw = "0"

        if raw == "0":
            print("Bye.")
            break
        if raw in menus:
            _, fn = menus[raw]
            try:
                fn(conn)
            except psycopg2.Error as exc:
                conn.rollback()
                print(f"  DB error: {exc}")
            except KeyboardInterrupt:
                print("\n  (interrupted — returning to main menu)")
        else:
            print("  Enter 0, 1, 2, or 3.")

    conn.close()


if __name__ == "__main__":
    main()
