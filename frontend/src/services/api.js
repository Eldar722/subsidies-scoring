import axios from 'axios'
import * as mockApi from './mockApi'

const USE_MOCK = import.meta.env.VITE_USE_MOCK === 'true'

const _api = axios.create({
  baseURL: import.meta.env.VITE_API_URL || 'http://localhost:8000',
  timeout: 15000,
})

_api.interceptors.response.use(
  (response) => response.data,
  (error) => {
    console.error('API Error:', error.response?.data || error.message)
    return Promise.reject(error)
  }
)

export const getHealth = USE_MOCK ? mockApi.getHealth : () => _api.get('/health')
export const getStats = USE_MOCK ? mockApi.getStats : () => _api.get('/api/stats')
export const getMetrics = USE_MOCK ? mockApi.getMetrics : () => _api.get('/api/metrics')
export const getShortlist = USE_MOCK ? mockApi.getShortlist : (topN = 20) => _api.get('/api/shortlist', { params: { top_n: topN } })
export const getProducers = USE_MOCK ? mockApi.getProducers : (params = {}) => _api.get('/api/producers', { params })
export const getProducerDetail = USE_MOCK ? mockApi.getProducerDetail : (id) => _api.get(`/api/producers/${id}`)
export const getProducerAdvice = USE_MOCK ? mockApi.getProducerAdvice : (id) => _api.get(`/api/producers/${id}/advice`)
export const getFairness = USE_MOCK ? mockApi.getFairness : () => _api.get('/api/fairness')
export const getMapRegions = USE_MOCK ? mockApi.getMapRegions : () => _api.get('/api/map/regions')
export const runSimulation = USE_MOCK ? mockApi.runSimulation : (weights, topN = 20) => _api.post('/api/simulate', { weights, top_n: topN })
export const runPipeline = USE_MOCK ? mockApi.runPipeline : () => _api.post('/api/pipeline/run')

export default _api
