import { useQuery } from '@tanstack/react-query'
import { getProducers } from '../services/api'

export function useProducers(params = {}) {
  return useQuery({
    queryKey: ['producers', params],
    queryFn: () => getProducers(params),
    staleTime: 5_000,
    gcTime: 60_000,
  })
}
