import { useQuery } from '@tanstack/react-query'
import { getProducers } from '../services/api'

export function useProducers(params = {}) {
  return useQuery({
    queryKey: ['producers', params],
    queryFn: () => getProducers(params),
    staleTime: 30_000,
  })
}
