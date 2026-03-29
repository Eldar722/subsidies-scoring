import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { Layout } from './components/layout/Layout'
import DashboardPage from './pages/DashboardPage'
import ProducerPage from './pages/ProducerPage'
import SimulatorPage from './pages/SimulatorPage'
import FairnessPage from './pages/FairnessPage'
import MapPage from './pages/MapPage'

const queryClient = new QueryClient({
  defaultOptions: { queries: { retry: 2, staleTime: 30_000 } }
})

export default function App() {
  return (
    <QueryClientProvider client={queryClient}>
      <BrowserRouter>
        <Layout>
          <Routes>
            <Route path="/" element={<Navigate to="/dashboard" replace />} />
            <Route path="/dashboard" element={<DashboardPage />} />
            <Route path="/producer/:id" element={<ProducerPage />} />
            <Route path="/simulator" element={<SimulatorPage />} />
            <Route path="/fairness" element={<FairnessPage />} />
            <Route path="/map" element={<MapPage />} />
          </Routes>
        </Layout>
      </BrowserRouter>
    </QueryClientProvider>
  )
}
