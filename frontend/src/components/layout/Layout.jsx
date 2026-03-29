import { Sidebar } from './Sidebar'

export function Layout({ children }) {
  return (
    <div style={{ display: 'flex' }}>
      <Sidebar />
      <main style={{ marginLeft: 240, flex: 1, minHeight: '100vh', padding: 32, background: '#F8FAFC' }}>
        {children}
      </main>
    </div>
  )
}
