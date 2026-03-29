import { useQuery } from '@tanstack/react-query'
import { getMapRegions } from '../services/api'

export function useMapRegions() {
  return useQuery({
    queryKey: ['mapRegions'],
    queryFn: getMapRegions,
    staleTime: 60_000,
  })
}
