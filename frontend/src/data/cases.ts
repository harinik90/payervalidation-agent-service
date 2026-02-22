/**
 * src/data/cases.ts
 *
 * All 16 synthetic prior-authorization cases embedded as TypeScript data.
 * Workflow cases (WF-001–WF-006) map directly to WORKFLOWS.md scenarios.
 * Clinical cases (CASE-2024-001–010) are happy-path clinical fixtures.
 */

export type Lob = 'commercial' | 'medicaid' | 'medicare_advantage'

export type ExpectedDecision =
  | 'APPROVE'
  | 'PEND'
  | 'DENY'
  | 'DENIED_HARD_STOP'
  | 'RETURNED_FOR_CORRECTION'

export interface CodingError {
  code: string
  type: string
  action: string
  bundled_into?: string
  primary?: string
}

export interface CaseDoc {
  case_id: string
  workflow: string
  expected_decision: ExpectedDecision
  member_id: string
  member_name: string
  dob: string
  lob: Lob
  npi: string
  provider_name: string
  facility_name: string
  service_date: string
  icd10_codes: string[]
  cpt_codes: string[]
  clinical_notes: string
  procedure_description: string
  policy_reference: string | null
  state?: string
  submission_note?: string
  leie_test_note?: string
  regulatory_test_note?: string
  coding_errors?: CodingError[]
}

// ── Workflow cases — map 1:1 to WORKFLOWS.md ─────────────────────────────────

export const WORKFLOW_CASES: CaseDoc[] = [
  {
    case_id: 'WF-001',
    workflow: 'WF1 — APPROVE',
    expected_decision: 'APPROVE',
    member_id: 'M-1234567',
    member_name: 'Harold R. Cooper',
    dob: '1958-06-14',
    lob: 'commercial',
    npi: '1234567890',
    provider_name: 'Riverside Orthopedic Group',
    facility_name: 'Riverside Orthopedic Surgery Center',
    service_date: '2025-10-15',
    icd10_codes: ['M1711'],
    cpt_codes: ['27447'],
    clinical_notes:
      'Patient is a 66-year-old male with right knee primary osteoarthritis confirmed on weight-bearing AP ' +
      'and lateral X-rays demonstrating Grade IV Kellgren-Lawrence changes (complete medial joint space ' +
      'obliteration, large osteophytes, subchondral sclerosis). Conservative therapy documented and failed ' +
      'over 8 months: physical therapy (16 sessions, inadequate relief), NSAIDs (meloxicam 15mg daily x ' +
      '6 months, GI tolerability issues), two intra-articular corticosteroid injections (March and June ' +
      '2025, transient relief only), weight management counseling (BMI 28.4). Functional impairment: ' +
      'unable to walk > 1 block, difficulty with stairs, limitations in ADLs. PCP medical clearance ' +
      'obtained. Cardiac clearance: normal EKG, cardiologist cleared for surgery. Requesting total knee ' +
      'arthroplasty (CPT 27447), right knee.',
    procedure_description: 'Right Total Knee Arthroplasty',
    policy_reference: 'CP-ORTHO-012',
    state: 'CA',
  },
  {
    case_id: 'WF-002',
    workflow: 'WF2 — PEND (missing docs)',
    expected_decision: 'PEND',
    member_id: 'M-7654321',
    member_name: 'Diane L. Foster',
    dob: '1967-03-29',
    lob: 'commercial',
    npi: '2233445566',
    provider_name: 'Advanced Spine and Neurology Center',
    facility_name: 'Advanced Spine Surgery Institute',
    service_date: '2025-10-28',
    icd10_codes: ['M54400'],
    cpt_codes: ['63685'],
    clinical_notes:
      'Patient referred for spinal cord stimulator (SCS) permanent implant for chronic low back pain ' +
      'with bilateral lower extremity radiation. Pain duration approximately 18 months following failed ' +
      'conservative management. Requesting authorization for permanent SCS implant (CPT 63685). ' +
      'Note: Supporting documentation including conservative therapy records, psychological evaluation, ' +
      'and SCS trial procedure note were not included with this submission.',
    procedure_description: 'Spinal Cord Stimulator Permanent Implant — Documentation Incomplete',
    policy_reference: 'CP-PM-004',
    state: 'TX',
    submission_note:
      'INCOMPLETE: Missing conservative_therapy_notes_6mo, psychological_evaluation_report, scs_trial_operative_report',
  },
  {
    case_id: 'WF-003',
    workflow: 'WF3 — DENY (plan exclusion)',
    expected_decision: 'DENY',
    member_id: 'M-2223334',
    member_name: 'Gloria M. Perez',
    dob: '1975-09-11',
    lob: 'commercial',
    npi: '3344556677',
    provider_name: 'Wellness Integrative Health',
    facility_name: 'Wellness Integrative Health Center',
    service_date: '2025-09-10',
    icd10_codes: ['M545'],
    cpt_codes: ['97810'],
    clinical_notes:
      'Patient is a 49-year-old female requesting acupuncture treatment for chronic low back pain. ' +
      'Patient preference for non-pharmacologic therapy. No prior acupuncture treatment. ' +
      'Provider is a licensed acupuncturist (LAc). Clinical notes state: chronic low back pain, ' +
      'patient preference for acupuncture, patient declines pharmacologic options.',
    procedure_description: 'Acupuncture — Chronic Low Back Pain',
    policy_reference: 'CP-COMP-011',
    state: 'FL',
  },
  {
    case_id: 'WF-004',
    workflow: 'WF4 — HARD STOP (OIG match)',
    expected_decision: 'DENIED_HARD_STOP',
    member_id: 'M-9876543',
    member_name: 'James T. Bradley',
    dob: '1962-01-15',
    lob: 'medicaid',
    npi: '1033472386',
    provider_name: 'Sunshine Pain Management LLC',
    facility_name: 'Sunshine Pain Management Clinic',
    service_date: '2025-11-01',
    icd10_codes: ['M545'],
    cpt_codes: ['64483'],
    clinical_notes:
      'Medicaid member requesting fluoroscopically guided lumbar epidural steroid injection for chronic ' +
      'radicular low back pain. ICD-10 M54.5. Provider NPI 1033472386. ' +
      'NOTE FOR TESTING: NPI 1033472386 is present in the OIG LEIE database (excl_type 1128a1, ' +
      'excl_date 20260219). This case should trigger a hard stop at the sanctions check and halt all ' +
      'downstream processing.',
    procedure_description: 'Lumbar Epidural Steroid Injection — LEIE-Excluded Provider',
    policy_reference: null,
    state: 'OH',
    leie_test_note: 'NPI 1033472386 confirmed in leie.db (excl_type=1128a1, excl_date=20260219)',
  },
  {
    case_id: 'WF-005',
    workflow: 'WF5 — PEND (regulatory override)',
    expected_decision: 'PEND',
    member_id: 'M-4445556',
    member_name: 'Evelyn N. Carter',
    dob: '1950-04-22',
    lob: 'medicare_advantage',
    npi: '5566778899',
    provider_name: 'Lakeside Endocrinology',
    facility_name: 'Lakeside Endocrinology Associates',
    service_date: '2025-08-05',
    icd10_codes: ['E119'],
    cpt_codes: ['95250'],
    clinical_notes:
      'Patient is a 75-year-old female Medicare Advantage member with Type 2 diabetes mellitus without ' +
      'complications (ICD-10 E11.9). Currently managed with metformin 1000mg BID and empagliflozin 10mg ' +
      'daily. Patient is NOT on insulin therapy. HbA1c: 7.8% (2025-07-15). No hypoglycemic episodes. ' +
      'Requesting continuous glucose monitoring (CGM, Dexcom G7, CPT 95250) for glucose trend monitoring ' +
      'and optimization of oral medication therapy. NOTE: Internal policy restricts commercial CGM to ' +
      'insulin-dependent patients. Medicare Advantage eligibility should be evaluated against CMS NCD ' +
      '280.1 (amended January 2025), which expanded coverage to all Medicare T2D patients regardless of ' +
      'insulin use.',
    procedure_description: 'CGM — Medicare Advantage Non-Insulin T2D (Regulatory Override Test)',
    policy_reference: 'CP-DM-001',
    state: 'OH',
    regulatory_test_note:
      'Expected: policy DENY overridden by CMS NCD 280.1 amendment (eff. 2025-01-01) -> PEND for manual review',
  },
  {
    case_id: 'WF-006',
    workflow: 'WF6 — RETURNED (coding error)',
    expected_decision: 'RETURNED_FOR_CORRECTION',
    member_id: 'M-3334455',
    member_name: 'Arthur P. Quinn',
    dob: '1955-11-30',
    lob: 'commercial',
    npi: '4455667788',
    provider_name: 'Metro Orthopaedic Surgery',
    facility_name: 'Metro Surgical Center',
    service_date: '2025-11-12',
    icd10_codes: ['M1711', 'M25361'],
    cpt_codes: ['27447', '27370'],
    clinical_notes:
      'Patient is a 69-year-old male with right knee primary osteoarthritis (M17.11), Grade IV on ' +
      'weight-bearing X-ray. Failed conservative therapy. Requesting right total knee arthroplasty ' +
      '(CPT 27447) with intraoperative knee injection (CPT 27370). Secondary diagnosis: stiffness of ' +
      'right knee (M25.361). NOTE: This submission contains intentional coding errors: (1) CPT 27370 is ' +
      'a CCI component of 27447 and cannot be billed separately on the same DOS; (2) ICD-10 M25.361 is ' +
      'clinically redundant when M17.11 is the primary diagnosis.',
    procedure_description: 'Right TKA with CCI Bundle Error (Coding Test)',
    policy_reference: 'CP-ORTHO-012',
    state: 'IL',
    coding_errors: [
      { code: '27370', type: 'CCI_BUNDLE', bundled_into: '27447', action: 'REMOVE' },
      { code: 'M25361', type: 'REDUNDANT_DX', primary: 'M1711', action: 'REVIEW' },
    ],
  },
]

// ── Clinical cases — happy-path fixtures ──────────────────────────────────────

export const CLINICAL_CASES: CaseDoc[] = [
  {
    case_id: 'CASE-2024-001',
    workflow: 'clinical',
    expected_decision: 'APPROVE',
    member_id: 'MBR-100001',
    member_name: 'Jane A. Doe',
    dob: '1972-04-15',
    lob: 'commercial',
    npi: '1234567890',
    provider_name: 'Dr. Sarah Chen, MD — Endocrinology Associates',
    facility_name: 'Riverside Medical Center',
    service_date: '2025-03-01',
    icd10_codes: ['E1100', 'E1165'],
    cpt_codes: ['95250', 'K0553'],
    clinical_notes:
      'Patient is a 52-year-old female with a 14-year history of Type 2 diabetes mellitus, currently on ' +
      'basal-bolus insulin regimen (glargine 30 units QHS, aspart 8 units TID with meals). Most recent ' +
      'HbA1c: 9.2% (dated 2025-02-10). Patient has experienced 4 symptomatic hypoglycemic episodes in the ' +
      'past 3 months (BG < 65 mg/dL), including one episode requiring assistance. Requesting authorization ' +
      'for CGM (Dexcom G7). Patient completed DSME program January 2025.',
    procedure_description: 'Continuous Glucose Monitoring — Dexcom G7 CGM System',
    policy_reference: 'CP-DM-001',
    state: 'CA',
  },
  {
    case_id: 'CASE-2024-002',
    workflow: 'clinical',
    expected_decision: 'APPROVE',
    member_id: 'MBR-100002',
    member_name: 'Robert B. Smith',
    dob: '1978-09-22',
    lob: 'commercial',
    npi: '1234567891',
    provider_name: 'Dr. Michael Torres, MD — Bariatric Surgery Center',
    facility_name: 'Metro Surgical Institute',
    service_date: '2025-04-15',
    icd10_codes: ['E6601', 'E1100', 'I10', 'Z6843'],
    cpt_codes: ['43644'],
    clinical_notes:
      'Patient is a 46-year-old male with BMI 42.3 kg/m2, T2D (HbA1c 8.8%), hypertension, and ' +
      'obstructive sleep apnea. Completed 7-month medically supervised weight management program. ' +
      'Psychological evaluation cleared patient. Nutritional counseling (4 sessions) completed. ' +
      'PCP medical clearance obtained. Requesting Roux-en-Y gastric bypass (CPT 43644).',
    procedure_description: 'Roux-en-Y Gastric Bypass',
    policy_reference: 'CP-BS-002',
    state: 'NY',
  },
  {
    case_id: 'CASE-2024-003',
    workflow: 'clinical',
    expected_decision: 'APPROVE',
    member_id: 'MBR-100003',
    member_name: 'Patricia C. Johnson',
    dob: '1965-11-08',
    lob: 'commercial',
    npi: '1234567892',
    provider_name: 'Dr. Aisha Williams, MD — Rheumatology Specialists',
    facility_name: 'University Rheumatology Clinic',
    service_date: '2025-02-20',
    icd10_codes: ['M0510', 'M0520'],
    cpt_codes: ['J0135'],
    clinical_notes:
      'Patient is a 59-year-old female with seropositive RA (DAS28-CRP: 4.8). Prior DMARD therapy: ' +
      'MTX 20mg/week x 18 months (hepatotoxicity), HCQ 400mg/day x 12 months (inadequate response). ' +
      'TB IGRA negative. HBsAg negative. Requesting adalimumab biosimilar (Hadlima, J0135).',
    procedure_description: 'Adalimumab Biosimilar (Hadlima) — Biologic DMARD for RA',
    policy_reference: 'CP-RA-003',
    state: 'IL',
  },
  {
    case_id: 'CASE-2024-004',
    workflow: 'clinical',
    expected_decision: 'APPROVE',
    member_id: 'MBR-100004',
    member_name: 'Thomas D. Martinez',
    dob: '1958-03-17',
    lob: 'medicare_advantage',
    npi: '1234567893',
    provider_name: 'Dr. Kevin Park, MD — Neurosurgery & Pain Management',
    facility_name: 'Advanced Spine Center',
    service_date: '2025-05-01',
    icd10_codes: ['M5416', 'G89211', 'M5417'],
    cpt_codes: ['63650', '63685'],
    clinical_notes:
      'Patient is a 66-year-old male with FBSS following L4-L5 discectomy (2021) and L3-S1 fusion (2022). ' +
      'Persistent bilateral radiculopathy, NRS pain 8/10. Conservative therapy failed: NSAIDs, opioids, ' +
      'PT (24 sessions), 3 ESI series. Psychological evaluation cleared (Dr. Amy Cho, PhD, 2025-01-05). ' +
      'Requesting SCS trial (CPT 63650); if >= 50% pain reduction, permanent implant to follow.',
    procedure_description: 'Spinal Cord Stimulator Trial and Permanent Implant',
    policy_reference: 'CP-PM-004',
    state: 'FL',
  },
  {
    case_id: 'CASE-2024-005',
    workflow: 'clinical',
    expected_decision: 'APPROVE',
    member_id: 'MBR-100005',
    member_name: 'Eleanor E. Thompson',
    dob: '1940-07-30',
    lob: 'medicare_advantage',
    npi: '1234567894',
    provider_name: 'Dr. James Wilson, MD — Orthopedics',
    facility_name: 'Riverside Orthopedic Hospital',
    service_date: '2025-03-15',
    icd10_codes: ['Z741', 'Z9911', 'M1611'],
    cpt_codes: ['99500', '99506'],
    clinical_notes:
      '84-year-old female, 5 days post left total hip arthroplasty. Homebound: cannot ambulate without ' +
      'walker. Ordering skilled nursing (wound care, warfarin monitoring), PT 3x/week, OT 2x/week. ' +
      'Face-to-face encounter completed day of discharge. Plan of Care signed by surgeon. ' +
      'Requesting 60-day home health episode.',
    procedure_description: 'Home Health Services — Post-Hip Replacement Rehabilitation',
    policy_reference: 'CP-HH-005',
    state: 'MA',
  },
  {
    case_id: 'CASE-2024-006',
    workflow: 'clinical',
    expected_decision: 'APPROVE',
    member_id: 'MBR-100006',
    member_name: 'Marcus F. Davis',
    dob: '1990-12-05',
    lob: 'commercial',
    npi: '1234567895',
    provider_name: 'Dr. Rebecca Stone, MD — Psychiatry',
    facility_name: 'Northside Behavioral Health Center',
    service_date: '2025-02-18',
    icd10_codes: ['F331', 'F41', 'F1010'],
    cpt_codes: ['90837', '90853', 'H0015'],
    clinical_notes:
      '34-year-old male, PHQ-9: 18/27, passive SI without plan, alcohol use disorder mild (last drink ' +
      '5 days ago). LOCUS score: 19 (High Intensity Community-Based). Does not meet inpatient criteria. ' +
      'Prior outpatient therapy: 32 sessions CBT. Requesting PHP: 20 hours/week.',
    procedure_description: 'Partial Hospitalization Program (PHP) — Mental Health and SUD',
    policy_reference: 'CP-BH-006',
    state: 'GA',
  },
  {
    case_id: 'CASE-2024-007',
    workflow: 'clinical',
    expected_decision: 'APPROVE',
    member_id: 'MBR-100007',
    member_name: 'Sandra G. Lee',
    dob: '1968-02-14',
    lob: 'commercial',
    npi: '1234567896',
    provider_name: 'Dr. David Brown, MD — Orthopedics',
    facility_name: 'Community Orthopedic Center',
    service_date: '2025-01-20',
    icd10_codes: ['M1711', 'M25561', 'M25562'],
    cpt_codes: ['97110', '97140', '97530'],
    clinical_notes:
      '57-year-old female, 3 weeks post right TKA (done 2024-12-30). Baseline LEFS: 28/80. At visit 12: ' +
      'LEFS improved to 42/80 (50% improvement), ROM improved to 0-105 deg. Requesting additional 18 PT ' +
      'visits to complete rehabilitation.',
    procedure_description: 'Outpatient Physical Therapy — Post-Total Knee Arthroplasty',
    policy_reference: 'CP-PT-007',
    state: 'WA',
  },
  {
    case_id: 'CASE-2024-008',
    workflow: 'clinical',
    expected_decision: 'APPROVE',
    member_id: 'MBR-100008',
    member_name: 'Christopher H. Nguyen',
    dob: '1985-06-20',
    lob: 'commercial',
    npi: '1234567897',
    provider_name: 'Dr. Jennifer Walsh, MD — Endocrinology',
    facility_name: 'Diabetes & Endocrine Specialists',
    service_date: '2025-03-10',
    icd10_codes: ['E1040', 'E1065'],
    cpt_codes: ['E0784', 'A9274', 'A9276'],
    clinical_notes:
      '39-year-old male, T1D since age 12. MDI: glargine 22u QHS + lispro TID. HbA1c: 8.4%. ' +
      'Hypoglycemia unawareness (Clarke score 5), 3 severe episodes past 6 months. Pump training ' +
      'completed (4-hr CDE program, 2025-02-28). SMBG logs 30 days compliant >= 4/day. ' +
      'Requesting Omnipod 5 insulin pump (HCPCS E0784).',
    procedure_description: 'Insulin Infusion Pump (Omnipod 5) — T1D with Hypoglycemia Unawareness',
    policy_reference: 'CP-DM-008',
    state: 'TX',
  },
  {
    case_id: 'CASE-2024-009',
    workflow: 'clinical',
    expected_decision: 'APPROVE',
    member_id: 'MBR-100009',
    member_name: 'Barbara I. Wilson',
    dob: '1950-08-11',
    lob: 'medicare_advantage',
    npi: '1234567898',
    provider_name: 'Dr. Steven Grant, MD — Gastroenterology',
    facility_name: 'Digestive Disease Associates',
    service_date: '2025-04-05',
    icd10_codes: ['Z1211', 'D1201', 'K631'],
    cpt_codes: ['45385'],
    clinical_notes:
      '74-year-old female. Prior colonoscopy (2022-09-15): 3 tubular adenomas removed. Per ACG 2023 ' +
      'guidelines: high-risk adenoma -> 3-year surveillance interval. Family history: mother with colon ' +
      'cancer at age 67. Requesting 3-year surveillance colonoscopy with polypectomy (CPT 45385).',
    procedure_description: 'Surveillance Colonoscopy with Polypectomy — High-Risk Adenoma History',
    policy_reference: 'CP-GI-009',
    state: 'AZ',
  },
  {
    case_id: 'CASE-2024-010',
    workflow: 'clinical',
    expected_decision: 'APPROVE',
    member_id: 'MBR-100010',
    member_name: 'William J. Garcia',
    dob: '1955-01-25',
    lob: 'commercial',
    npi: '1234567899',
    provider_name: 'Dr. Priya Sharma, MD — Thoracic Oncology',
    facility_name: 'Comprehensive Cancer Center',
    service_date: '2025-03-25',
    icd10_codes: ['C3492', 'C7800', 'Z8501'],
    cpt_codes: ['J9271'],
    clinical_notes:
      '70-year-old male, Stage IV NSCLC adenocarcinoma, right lower lobe with bilateral pulmonary mets. ' +
      'EGFR/ALK/ROS1/KRAS neg. PD-L1 TPS 78% (22C3). TMB 12 mut/Mb. ECOG PS: 1. ' +
      'Requesting first-line pembrolizumab monotherapy (Keytruda, J9271) per NCCN Cat 1. ' +
      'No autoimmune disease. Dose: 200mg IV q3w x 8 cycles.',
    procedure_description: 'Pembrolizumab (Keytruda) First-Line — Stage IV NSCLC PD-L1 High',
    policy_reference: 'CP-ONC-010',
    state: 'CO',
  },
]

export const ALL_CASES: CaseDoc[] = [...WORKFLOW_CASES, ...CLINICAL_CASES]

export function findCase(caseId: string): CaseDoc | undefined {
  return ALL_CASES.find((c) => c.case_id === caseId)
}
