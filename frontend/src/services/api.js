import axios from 'axios'
import * as mockApi from './mockApi'
import { supabase } from '../lib/supabase'

const USE_MOCK = import.meta.env.VITE_USE_MOCK === 'true'

const _api = axios.create({
  baseURL: import.meta.env.VITE_API_URL || 'http://localhost:8000',
  timeout: 30000,
})

// Attach Supabase auth token to every request
_api.interceptors.request.use(async (config) => {
  try {
    const { data: { session } } = await supabase.auth.getSession()
    if (session?.access_token) {
      config.headers.Authorization = `Bearer ${session.access_token}`
    }
  } catch {
    // Continue without auth — backend will handle unauthenticated requests
  }
  return config
})

_api.interceptors.response.use(
  (response) => response.data,
  (error) => {
    console.error('API Error:', error.response?.data || error.message)
    return Promise.reject(error)
  }
)

// Основные endpoints
export const getHealth = USE_MOCK ? mockApi.getHealth : () => _api.get('/health')
export const getStats = USE_MOCK ? mockApi.getStats : () => _api.get('/api/stats')
export const getMetrics = USE_MOCK ? mockApi.getMetrics : () => _api.get('/api/metrics')
export const getShortlist = USE_MOCK ? mockApi.getShortlist : (topN = 20) => _api.get('/api/shortlist', { params: { top_n: topN } })
export const getProducers = USE_MOCK ? mockApi.getProducers : (params = {}) => _api.get('/api/producers', { params })
export const getProducerDetail = USE_MOCK ? mockApi.getProducerDetail : (id) => _api.get(`/api/producers/${id}`)
export const getProducerAdvice = USE_MOCK ? mockApi.getProducerAdvice : (id) => _api.get(`/api/producers/${id}/advice`)
export const getProducerRisk = (id) => _api.get(`/api/producers/${id}/risk`)
export const getFairness = USE_MOCK ? mockApi.getFairness : () => _api.get('/api/fairness')
export const getMapRegions = USE_MOCK ? mockApi.getMapRegions : () => _api.get('/api/map/regions')
export const runSimulation = USE_MOCK ? mockApi.runSimulation : (weights, topN = 20) => _api.post('/api/simulate', { weights, top_n: topN })

// Pipeline
export const runPipeline = USE_MOCK ? mockApi.runPipeline : () => _api.post('/api/pipeline/run')
export const getPipelineStatus = () => _api.get('/api/pipeline/status')

// Audit
export const getAuditLedger = (limit = 50) => _api.get('/api/audit/ledger', { params: { limit } })

// Analytics
export const getSubsidyEffectiveness = USE_MOCK ? mockApi.getSubsidyEffectiveness : () => _api.get('/api/analytics/subsidy-effectiveness')
export const getRedFlags = USE_MOCK ? mockApi.getRedFlags : () => _api.get('/api/analytics/red-flags')

// Drift Monitor (Feature 1)
export const getDriftStatus = USE_MOCK ? mockApi.getDriftStatus : () => _api.get('/api/drift/status')
export const getProducerConfidence = USE_MOCK ? mockApi.getProducerConfidence : (id) => _api.get(`/api/confidence/${id}`)

// Fair Reranking (Feature 2)
export const getFairShortlist = USE_MOCK ? mockApi.getFairShortlist : (params = {}) => _api.get('/api/shortlist/fair', { params })

// Counterfactual Explanations (Feature 3)
export const getCounterfactual = USE_MOCK ? mockApi.getCounterfactual : (id) => _api.get(`/api/producers/${id}/counterfactual`)

export default _api
