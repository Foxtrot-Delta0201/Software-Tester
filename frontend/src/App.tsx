import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom'
import Sidebar from './components/Sidebar'
import Dashboard from './pages/Dashboard'
import DataSeeder from './pages/DataSeeder'
import TestRunner from './pages/TestRunner'
import TestCatalog from './pages/TestCatalog'
import Results from './pages/Results'
import Settings from './pages/Settings'
import CyberMode from './pages/CyberMode'
import SandboxPage from './pages/SandboxPage'

export default function App() {
  return (
    <BrowserRouter>
      <div className="flex h-screen overflow-hidden" style={{ background: 'var(--bg-base)' }}>
        <Sidebar />
        <main className="flex-1 overflow-y-auto scrollbar-thin">
          <Routes>
            <Route path="/"         element={<Dashboard />} />
            <Route path="/seed"     element={<DataSeeder />} />
            <Route path="/tests"    element={<TestRunner />} />
            <Route path="/catalog"  element={<TestCatalog />} />
            <Route path="/cyber"    element={<CyberMode />} />
            <Route path="/sandbox"  element={<SandboxPage />} />
            <Route path="/results"  element={<Results />} />
            <Route path="/settings" element={<Settings />} />
            <Route path="*"         element={<Navigate to="/" replace />} />
          </Routes>
        </main>
      </div>
    </BrowserRouter>
  )
}
