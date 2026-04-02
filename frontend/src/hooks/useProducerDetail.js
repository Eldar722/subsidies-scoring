import { useQuery } from '@tanstack/react-query'
import { getProducerDetail } from '../services/api'

export function useProducerDetail(id) {
  return useQuery({
    queryKey: ['producer', id],
    queryFn: () => getProducerDetail(id),
    enabled: !!id,
    staleTime: 10_000,
    gcTime: 60_000,
  })
}
