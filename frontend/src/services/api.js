import axios from 'axios'

const api = axios.create({
  baseURL: import.meta.env.VITE_API_URL || 'http://localhost:8000',
  timeout: 15000,
})

api.interceptors.response.use(
  (response) => response.data,
  (error) => {
    console.error('API Error:', error.response?.data || error.message)
    return Promise.reject(error)
  }
)

export const getHealth = () => api.get('/health')
export const getMetrics = () => api.get('/api/metrics')
export const getStats = () => api.get('/api/stats')
export const getShortlist = (topN = 20) => api.get('/api/shortlist', { params: { top_n: topN } })
export const getProducers = (params = {}) => api.get('/api/producers', { params })
export const getProducerDetail = (id) => api.get(`/api/producers/${id}`)
export const getProducerAdvice = (id) => api.get(`/api/producers/${id}/advice`)
export const getFairness = () => api.get('/api/fairness')
export const getMapRegions = () => api.get('/api/map/regions')
export const runSimulation = (weights, topN = 20) =>
  api.post('/api/simulate', { weights, top_n: topN })
export const runPipeline = () => api.post('/api/pipeline/run')

export default api
