export interface Resume {
  id: number | string
  filename: string
  created_at?: string
  uploaded_at?: string
}

export interface Job {
  id: number | string
  title: string
  company: string
  description?: string
  requirements?: string
}

export interface MatchResult {
  job_id: number | string
  title: string
  company: string
  score: number
  explanation: { summary: string }
}

export interface MatchResponse {
  resume_id: number | string
  total_jobs: number
  results: MatchResult[]
}