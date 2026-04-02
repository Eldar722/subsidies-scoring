import { useQuery } from '@tanstack/react-query'
import { getFairness } from '../services/api'

export function useFairness() {
  return useQuery({
    queryKey: ['fairness'],
    queryFn: getFairness,
    staleTime: 5_000,
    gcTime: 60_000,
  })
}
