import { useEffect, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import api from '@/api/client'
import { getEmailFromToken } from '@/lib/helpers'
import type { Job, Resume } from '@/lib/types'
import { DashboardHeader } from '@/components/DashboardHeader'
import { ResumesColumn } from '@/components/ResumesColumn'
import { JobsColumn } from '@/components/JobsColumn'
import { MatchesColumn } from '@/components/MatchesColumn'

export default function DashboardPage() {
  const navigate = useNavigate()
  const [resumes, setResumes] = useState<Resume[]>([])
  const [jobs, setJobs] = useState<Job[]>([])
  const [email] = useState(() => getEmailFromToken(localStorage.getItem('token')))

  useEffect(() => {
    if (!localStorage.getItem('token')) {
      navigate('/')
      return
    }
    let active = true
    ;(async () => {
      try {
        const [resumesRes, jobsRes] = await Promise.all([
          api.get<Resume[]>('/resumes/'),
          api.get<Job[]>('/jobs/'),
        ])
        if (!active) return
        setResumes(resumesRes.data ?? [])
        setJobs(jobsRes.data ?? [])
      } catch {
        /* interceptor handles 401; other errors leave empty lists */
      }
    })()
    return () => {
      active = false
    }
  }, [navigate])

  return (
    <div className="min-h-screen bg-background">
      <DashboardHeader email={email} />
      <main className="mx-auto max-w-7xl px-4 py-6 sm:px-6">
        <div className="grid grid-cols-1 items-start gap-5 lg:grid-cols-3">
          <ResumesColumn resumes={resumes} setResumes={setResumes} />
          <JobsColumn jobs={jobs} setJobs={setJobs} />
          <MatchesColumn resumes={resumes} jobs={jobs} />
        </div>
      </main>
    </div>
  )
}
