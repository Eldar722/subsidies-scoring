import { useMutation } from '@tanstack/react-query'
import { runSimulation } from '../services/api'

export function useSimulator() {
  const mutation = useMutation({ mutationFn: ({ weights, topN }) => runSimulation(weights, topN) })
  return {
    simulate: mutation.mutate,
    data: mutation.data,
    isLoading: mutation.isPending,
    error: mutation.error,
  }
}
