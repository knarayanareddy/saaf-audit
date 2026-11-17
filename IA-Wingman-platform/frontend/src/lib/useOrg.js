import { useQuery } from '@tanstack/react-query'
import client from '../api/client'

// The white-label organization profile (name, brand colour, entities). Cached
// hard — it changes rarely. A sensible fallback keeps the UI usable offline.
const FALLBACK = {
  name: 'IA Wingman',
  short_name: 'IA Wingman',
  sector: 'internal audit',
  tagline: 'Internal Audit',
  brand_hex: '#1E6B4F',
  entities: [],
  audit_types: [],
}

export function useOrg() {
  const { data } = useQuery({
    queryKey: ['org'],
    queryFn: () => client.get('/org').then((r) => r.data),
    staleTime: Infinity,
  })
  return data || FALLBACK
}
