import { useQuery } from '@tanstack/react-query'
import { getMapRegions } from '../services/api'

export function useMapRegions() {
  return useQuery({
    queryKey: ['mapRegions'],
    queryFn: getMapRegions,
    staleTime: 10_000,
    gcTime: 300_000,  // Keep in cache for 5 min since geo data is static
  })
}
