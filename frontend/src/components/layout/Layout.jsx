import { Outlet } from 'react-router-dom'
import { Sidebar } from './Sidebar'
import { Header } from './Header'

export function Layout({ children }) {
  return (
    <div className="flex min-h-screen" style={{ background: 'var(--bg-page)' }}>
      <Sidebar />
      <div
        className="flex-1 flex flex-col min-w-0"
        style={{ marginLeft: 'var(--sidebar-width, 240px)' }}
      >
        <Header />
        <main className="flex-1 p-6 lg:p-8 overflow-auto" style={{ color: 'var(--text-primary)' }}>
          {children ?? <Outlet />}
        </main>
      </div>
    </div>
  )
}
