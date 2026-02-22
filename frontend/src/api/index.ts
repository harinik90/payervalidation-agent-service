/**
 * src/api/index.ts
 *
 * API client for the Python orchestrator REST facade.
 * No PHI is held in frontend state beyond the active session.
 */

const BASE_URL = '/api'

export interface PARequest {
  member_id: string
  npi: string
  provider_name: string
  icd10_codes: string[]
  cpt_codes: string[]
  lob: 'commercial' | 'medicaid' | 'medicare_advantage'
  service_date: string
  clinical_notes?: string
  state?: string
}

export interface PAResponse {
  decision: 'APPROVE' | 'DENY' | 'PEND' | 'RETURNED_FOR_CORRECTION' | 'DENIED'
  hard_stop: boolean
  policy_refs: string[]
  doc_requirements: string[]
  reason?: string
  coding_issues?: Array<{ code: string; issue: string }>
  regulatory_refs?: string[]
}

export async function submitPriorAuth(request: PARequest): Promise<PAResponse> {
  const response = await fetch(`${BASE_URL}/prior-auth`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(request),
  })

  if (!response.ok) {
    throw new Error(`Prior auth request failed: ${response.status} ${response.statusText}`)
  }

  return response.json() as Promise<PAResponse>
}
