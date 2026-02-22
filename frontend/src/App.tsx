import { useState, type FC, type ChangeEvent, type FormEvent } from 'react'
import { submitPriorAuth, type PARequest, type PAResponse } from '@/api/index'
import {
  ALL_CASES,
  WORKFLOW_CASES,
  CLINICAL_CASES,
  findCase,
  type CaseDoc,
  type ExpectedDecision,
} from '@/data/cases'

// ── Decision badge helpers ────────────────────────────────────────────────────

const DECISION_META: Record<
  string,
  { icon: string; label: string; bannerClass: string }
> = {
  APPROVE:                  { icon: '✓', label: 'APPROVED',            bannerClass: 'banner-APPROVE' },
  PEND:                     { icon: '⏸', label: 'PENDING',             bannerClass: 'banner-PEND' },
  DENY:                     { icon: '✕', label: 'DENIED',              bannerClass: 'banner-DENY' },
  DENIED:                   { icon: '⛔', label: 'DENIED — HARD STOP', bannerClass: 'banner-DENIED' },
  RETURNED_FOR_CORRECTION:  { icon: '↩', label: 'RETURNED FOR CORRECTION', bannerClass: 'banner-RETURNED_FOR_CORRECTION' },
}

const EXPECTED_LABEL: Record<ExpectedDecision, string> = {
  APPROVE:                  'Expected: APPROVE',
  PEND:                     'Expected: PEND',
  DENY:                     'Expected: DENY',
  DENIED_HARD_STOP:         'Expected: HARD STOP',
  RETURNED_FOR_CORRECTION:  'Expected: RETURNED',
}

function ExpectedBadge({ decision }: { decision: ExpectedDecision }) {
  const cls = `expected-badge expected-${decision}`
  return <span className={cls}>{EXPECTED_LABEL[decision]}</span>
}

// ── Form state initialiser ────────────────────────────────────────────────────

function caseToForm(c: CaseDoc): PARequest {
  return {
    member_id:     c.member_id,
    npi:           c.npi,
    provider_name: c.provider_name,
    icd10_codes:   [...c.icd10_codes],
    cpt_codes:     [...c.cpt_codes],
    lob:           c.lob,
    service_date:  c.service_date,
    clinical_notes: c.clinical_notes,
    state:         c.state,
  }
}

const EMPTY_FORM: PARequest = {
  member_id: '',
  npi: '',
  provider_name: '',
  icd10_codes: [],
  cpt_codes: [],
  lob: 'commercial',
  service_date: '',
  clinical_notes: '',
  state: '',
}

// ── Main component ────────────────────────────────────────────────────────────

const App: FC = () => {
  const [selectedCaseId, setSelectedCaseId] = useState<string>('')
  const [form, setForm]   = useState<PARequest>(EMPTY_FORM)
  const [status, setStatus] = useState<'idle' | 'loading' | 'success' | 'error'>('idle')
  const [result, setResult] = useState<PAResponse | null>(null)
  const [errorMsg, setErrorMsg] = useState<string>('')

  // Derived selected case object
  const selectedCase: CaseDoc | undefined = selectedCaseId ? findCase(selectedCaseId) : undefined

  // ── Handlers ──────────────────────────────────────────────────────────────

  function handleCaseSelect(e: ChangeEvent<HTMLSelectElement>) {
    const id = e.target.value
    setSelectedCaseId(id)
    setResult(null)
    setErrorMsg('')
    setStatus('idle')
    if (id) {
      const c = findCase(id)
      if (c) setForm(caseToForm(c))
    } else {
      setForm(EMPTY_FORM)
    }
  }

  function handleField(field: keyof PARequest) {
    return (e: ChangeEvent<HTMLInputElement | HTMLSelectElement | HTMLTextAreaElement>) => {
      setForm((f) => ({ ...f, [field]: e.target.value }))
    }
  }

  function handleCodesField(field: 'icd10_codes' | 'cpt_codes') {
    return (e: ChangeEvent<HTMLInputElement>) => {
      const codes = e.target.value
        .split(/[\s,]+/)
        .map((s) => s.trim())
        .filter(Boolean)
      setForm((f) => ({ ...f, [field]: codes }))
    }
  }

  async function handleSubmit(e: FormEvent) {
    e.preventDefault()
    setStatus('loading')
    setResult(null)
    setErrorMsg('')
    try {
      const res = await submitPriorAuth(form)
      setResult(res)
      setStatus('success')
    } catch (err) {
      setErrorMsg(err instanceof Error ? err.message : String(err))
      setStatus('error')
    }
  }

  // ── Render ────────────────────────────────────────────────────────────────

  return (
    <div className="app">
      {/* Header */}
      <header className="app-header">
        <h1>PayerAI GPT</h1>
        <span className="subtitle">Prior Authorization Platform — Development Console</span>
      </header>

      <div className="app-body">
        {/* ── Left panel: Case Selector ─────────────────────────────────── */}
        <div className="left-panel">
          <div className="card">
            <div className="card-title">Sample Case Loader</div>

            <select
              className="case-select"
              value={selectedCaseId}
              onChange={handleCaseSelect}
            >
              <option value="">— Select a case —</option>

              <optgroup label="── Workflow Scenarios (WORKFLOWS.md) ──">
                {WORKFLOW_CASES.map((c) => (
                  <option key={c.case_id} value={c.case_id}>
                    {c.case_id} · {c.workflow}
                  </option>
                ))}
              </optgroup>

              <optgroup label="── Clinical Cases (Happy Path) ──">
                {CLINICAL_CASES.map((c) => (
                  <option key={c.case_id} value={c.case_id}>
                    {c.case_id} · {c.procedure_description.split('—')[0].trim()}
                  </option>
                ))}
              </optgroup>
            </select>

            {/* Case info card */}
            {selectedCase && (
              <div className="case-info">
                <div className="case-info-row">
                  <span className="case-info-label">Member</span>
                  <span className="case-info-value">{selectedCase.member_name}</span>
                </div>
                <div className="case-info-row">
                  <span className="case-info-label">ID</span>
                  <span className="case-info-value">{selectedCase.member_id}</span>
                </div>
                <div className="case-info-row">
                  <span className="case-info-label">Provider NPI</span>
                  <span className="case-info-value">{selectedCase.npi}</span>
                </div>
                <div className="case-info-row">
                  <span className="case-info-label">LOB</span>
                  <span className="case-info-value">{selectedCase.lob}</span>
                </div>
                <div className="case-info-row">
                  <span className="case-info-label">Service Date</span>
                  <span className="case-info-value">{selectedCase.service_date}</span>
                </div>

                <hr className="case-info-divider" />

                <div className="case-info-row">
                  <span className="case-info-label">ICD-10</span>
                  <span className="case-info-value">{selectedCase.icd10_codes.join(', ')}</span>
                </div>
                <div className="case-info-row">
                  <span className="case-info-label">CPT/HCPCS</span>
                  <span className="case-info-value">{selectedCase.cpt_codes.join(', ')}</span>
                </div>
                {selectedCase.policy_reference && (
                  <div className="case-info-row">
                    <span className="case-info-label">Policy</span>
                    <span className="case-info-value">{selectedCase.policy_reference}</span>
                  </div>
                )}

                <hr className="case-info-divider" />

                <ExpectedBadge decision={selectedCase.expected_decision} />

                {/* Test notes for special scenarios */}
                {selectedCase.submission_note && (
                  <div className="test-note">
                    <strong>Submission Note</strong>
                    {selectedCase.submission_note}
                  </div>
                )}
                {selectedCase.leie_test_note && (
                  <div className="test-note">
                    <strong>LEIE Test</strong>
                    {selectedCase.leie_test_note}
                  </div>
                )}
                {selectedCase.regulatory_test_note && (
                  <div className="test-note">
                    <strong>Regulatory Override Test</strong>
                    {selectedCase.regulatory_test_note}
                  </div>
                )}
                {selectedCase.coding_errors && selectedCase.coding_errors.length > 0 && (
                  <div className="coding-errors">
                    <div className="result-section-title" style={{ marginTop: 8 }}>
                      Intentional Coding Errors
                    </div>
                    {selectedCase.coding_errors.map((e) => (
                      <span key={e.code} className="coding-error-chip">
                        {e.code} · {e.type} · {e.action}
                      </span>
                    ))}
                  </div>
                )}
              </div>
            )}

            {/* Quick-select buttons */}
            <div style={{ marginTop: 12, display: 'flex', flexWrap: 'wrap', gap: 6 }}>
              {ALL_CASES.map((c) => (
                <button
                  key={c.case_id}
                  onClick={() => {
                    setSelectedCaseId(c.case_id)
                    setForm(caseToForm(c))
                    setResult(null)
                    setErrorMsg('')
                    setStatus('idle')
                  }}
                  style={{
                    padding: '3px 8px',
                    fontSize: 11,
                    border: '1px solid',
                    borderRadius: 4,
                    cursor: 'pointer',
                    fontWeight: selectedCaseId === c.case_id ? 700 : 400,
                    borderColor: selectedCaseId === c.case_id ? '#3182ce' : '#cbd5e0',
                    background: selectedCaseId === c.case_id ? '#ebf8ff' : 'white',
                    color: selectedCaseId === c.case_id ? '#2b6cb0' : '#4a5568',
                    transition: 'all 0.1s',
                  }}
                >
                  {c.case_id}
                </button>
              ))}
            </div>
          </div>
        </div>

        {/* ── Right panel: Form + Results ───────────────────────────────── */}
        <div className="right-panel">
          <div className="card">
            <div className="card-title">Prior Authorization Request</div>

            <form onSubmit={handleSubmit}>
              <div className="form-grid">

                <div className="form-group">
                  <label htmlFor="member_id">Member ID</label>
                  <input
                    id="member_id"
                    type="text"
                    value={form.member_id}
                    onChange={handleField('member_id')}
                    placeholder="M-1234567"
                    required
                  />
                </div>

                <div className="form-group">
                  <label htmlFor="npi">Provider NPI</label>
                  <input
                    id="npi"
                    type="text"
                    value={form.npi}
                    onChange={handleField('npi')}
                    placeholder="1234567890"
                    required
                  />
                </div>

                <div className="form-group full-width">
                  <label htmlFor="provider_name">Provider Name</label>
                  <input
                    id="provider_name"
                    type="text"
                    value={form.provider_name}
                    onChange={handleField('provider_name')}
                    placeholder="Dr. Name, Specialty"
                    required
                  />
                </div>

                <div className="form-group">
                  <label htmlFor="icd10_codes">ICD-10 Codes</label>
                  <input
                    id="icd10_codes"
                    type="text"
                    value={form.icd10_codes.join(', ')}
                    onChange={handleCodesField('icd10_codes')}
                    placeholder="M1711, E119"
                  />
                  <span className="form-hint">Comma or space separated</span>
                </div>

                <div className="form-group">
                  <label htmlFor="cpt_codes">CPT / HCPCS Codes</label>
                  <input
                    id="cpt_codes"
                    type="text"
                    value={form.cpt_codes.join(', ')}
                    onChange={handleCodesField('cpt_codes')}
                    placeholder="27447, J9271"
                  />
                  <span className="form-hint">Comma or space separated</span>
                </div>

                <div className="form-group">
                  <label htmlFor="lob">Line of Business</label>
                  <select id="lob" value={form.lob} onChange={handleField('lob')}>
                    <option value="commercial">Commercial</option>
                    <option value="medicaid">Medicaid</option>
                    <option value="medicare_advantage">Medicare Advantage</option>
                  </select>
                </div>

                <div className="form-group">
                  <label htmlFor="service_date">Service Date</label>
                  <input
                    id="service_date"
                    type="date"
                    value={form.service_date}
                    onChange={handleField('service_date')}
                    required
                  />
                </div>

                <div className="form-group">
                  <label htmlFor="state">State</label>
                  <input
                    id="state"
                    type="text"
                    value={form.state ?? ''}
                    onChange={handleField('state')}
                    placeholder="CA"
                    maxLength={2}
                  />
                </div>

                <div className="form-group full-width">
                  <label htmlFor="clinical_notes">Clinical Notes</label>
                  <textarea
                    id="clinical_notes"
                    value={form.clinical_notes ?? ''}
                    onChange={handleField('clinical_notes')}
                    placeholder="Enter clinical notes supporting medical necessity…"
                    rows={6}
                  />
                </div>

              </div>

              <button
                type="submit"
                className="btn-submit"
                disabled={status === 'loading'}
              >
                {status === 'loading' ? (
                  <>
                    <span className="spinner" />
                    Submitting…
                  </>
                ) : (
                  'Submit Prior Authorization Request'
                )}
              </button>
            </form>
          </div>

          {/* ── Error ── */}
          {status === 'error' && (
            <div className="error-box">
              <strong>Error: </strong>{errorMsg}
            </div>
          )}

          {/* ── Decision result ── */}
          {status === 'success' && result && (
            <div className="card result-card">
              <div className="card-title">Decision</div>

              {/* Banner */}
              {(() => {
                const meta = DECISION_META[result.decision] ?? {
                  icon: '?', label: result.decision, bannerClass: 'banner-PEND',
                }
                return (
                  <div className={`decision-banner ${meta.bannerClass}`}>
                    <span className="decision-icon">{meta.icon}</span>
                    <div>
                      <div className="decision-text">{meta.label}</div>
                      {result.hard_stop && (
                        <div className="decision-sub">
                          OIG LEIE exclusion — all downstream processing halted. Audit log written.
                        </div>
                      )}
                    </div>
                  </div>
                )
              })()}

              {/* Reason */}
              {result.reason && (
                <div className="result-section">
                  <div className="result-section-title">Reason</div>
                  <div className="result-reason">{result.reason}</div>
                </div>
              )}

              {/* Policy refs */}
              {result.policy_refs && result.policy_refs.length > 0 && (
                <div className="result-section">
                  <div className="result-section-title">Policy References</div>
                  {result.policy_refs.map((ref) => (
                    <span key={ref} className="result-tag">{ref}</span>
                  ))}
                </div>
              )}

              {/* Regulatory refs */}
              {result.regulatory_refs && result.regulatory_refs.length > 0 && (
                <div className="result-section">
                  <div className="result-section-title">Regulatory References</div>
                  {result.regulatory_refs.map((ref) => (
                    <span key={ref} className="result-tag warn">{ref}</span>
                  ))}
                </div>
              )}

              {/* Documentation requirements */}
              {result.doc_requirements && result.doc_requirements.length > 0 && (
                <div className="result-section">
                  <div className="result-section-title">Documentation Required</div>
                  {result.doc_requirements.map((doc) => (
                    <span key={doc} className="result-tag">{doc}</span>
                  ))}
                </div>
              )}

              {/* Coding issues */}
              {result.coding_issues && result.coding_issues.length > 0 && (
                <div className="result-section">
                  <div className="result-section-title">Coding Issues</div>
                  {result.coding_issues.map((issue) => (
                    <div key={issue.code} style={{ marginBottom: 6 }}>
                      <span className="coding-error-chip">{issue.code}</span>
                      <span style={{ fontSize: 12, color: '#4a5568' }}>{issue.issue}</span>
                    </div>
                  ))}
                </div>
              )}
            </div>
          )}
        </div>
      </div>
    </div>
  )
}

export default App
