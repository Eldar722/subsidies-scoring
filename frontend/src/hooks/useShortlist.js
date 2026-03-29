import { useQuery } from '@tanstack/react-query'
import { getShortlist } from '../services/api'

export function useShortlist(topN = 20) {
  return useQuery({
    queryKey: ['shortlist', topN],
    queryFn: () => getShortlist(topN),
    staleTime: 30_000,
  })
}
