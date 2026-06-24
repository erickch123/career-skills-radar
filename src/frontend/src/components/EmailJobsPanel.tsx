import { useState, useEffect } from 'react'

interface EmailJob {
  index: number
  title: string
  company: string
  location: string
  job_url: string
  email_date: string
  email_subject: string
  source: 'linkedin' | 'indeed'
  already_saved: boolean
}

type RowState = 'idle' | 'adding' | 'saved'

interface Props {
  onClose: () => void
  onSaved: (msg: string) => void
}

export default function EmailJobsPanel({ onClose, onSaved }: Props) {
  const [jobs, setJobs] = useState<EmailJob[]>([])
  const [mode, setMode] = useState<'gmail' | 'demo'>('demo')
  const [rowStates, setRowStates] = useState<Record<number, RowState>>({})
  const [jdTexts, setJdTexts] = useState<Record<number, string>>({})
  const [savingIdx, setSavingIdx] = useState<number | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')

  useEffect(() => {
    fetch('/api/email/jobs')
      .then(r => r.json())
      .then(data => {
        setJobs(data.jobs || [])
        setMode(data.mode)
      })
      .catch(() => setError('Failed to load email alerts.'))
      .finally(() => setLoading(false))
  }, [])

  function startAdding(idx: number) {
    setRowStates(prev => ({ ...prev, [idx]: 'adding' }))
  }

  function cancelAdding(idx: number) {
    setRowStates(prev => ({ ...prev, [idx]: 'idle' }))
    setJdTexts(prev => { const n = { ...prev }; delete n[idx]; return n })
  }

  async function saveJob(job: EmailJob) {
    const jd = jdTexts[job.index]?.trim()
    if (!jd) return
    setSavingIdx(job.index)
    setError('')
    try {
      const res = await fetch('/api/jobs', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ title: job.title, company: job.company, jd_text: jd }),
      })
      const data = await res.json()
      if (!res.ok) { setError(data.detail || 'Failed to save.'); return }
      setRowStates(prev => ({ ...prev, [job.index]: 'saved' }))
      setJobs(prev => prev.map(j => j.index === job.index ? { ...j, already_saved: true } : j))
      onSaved(`${job.title} at ${job.company} saved — ${data.skills_found} skills found`)
    } catch {
      setError('Something went wrong. Please try again.')
    } finally {
      setSavingIdx(null)
    }
  }

  return (
    <div className="email-overlay">
      {/* ── Header ── */}
      <div className="email-overlay-header">
        <span className="email-overlay-title">
          Job Alerts
          <span className={`email-source-badge ${mode === 'gmail' ? 'email-source-live' : ''}`}>
            {mode === 'gmail' ? 'live Gmail' : 'demo data'}
          </span>
          {!loading && jobs.length > 0 && (
            <span className="email-count">{jobs.length} jobs</span>
          )}
        </span>
        <button className="paste-close" onClick={onClose}>✕</button>
      </div>

      {/* ── Body (scrollable) ── */}
      <div className="email-overlay-body">
        {loading && <div className="email-loading">Loading alerts…</div>}
        {error && <div className="email-error">{error}</div>}

        {!loading && jobs.length === 0 && (
          <div className="jobs-empty">No job alert emails found.</div>
        )}

        {!loading && jobs.length > 0 && (
          <div className="email-jobs-list">
            {jobs.map(job => {
              const state = rowStates[job.index] ?? (job.already_saved ? 'saved' : 'idle')
              return (
                <div key={job.index} className={`email-job-card ${state === 'adding' ? 'email-job-card-open' : ''}`}>
                  {/* ── Job row ── */}
                  <div className="email-job-row">
                    <div className="email-job-info">
                      <div className="email-job-title">
                        <span className={`email-platform-tag email-platform-${job.source}`}>
                          {job.source === 'linkedin' ? 'LinkedIn' : 'Indeed'}
                        </span>
                        {job.title}
                      </div>
                      <div className="email-job-meta">
                        {job.company}
                        {job.location && ` · ${job.location}`}
                        {' · '}{job.email_date}
                      </div>
                    </div>
                    <div className="email-job-actions">
                      <a
                        href={job.job_url}
                        target="_blank"
                        rel="noopener noreferrer"
                        className="job-view"
                      >
                        View
                      </a>
                      {state === 'saved' && (
                        <span className="email-job-tag">saved ✓</span>
                      )}
                      {state === 'idle' && (
                        <button className="email-add-btn" onClick={() => startAdding(job.index)}>
                          + Add
                        </button>
                      )}
                      {state === 'adding' && (
                        <button className="email-add-btn email-add-btn-cancel" onClick={() => cancelAdding(job.index)}>
                          Cancel
                        </button>
                      )}
                    </div>
                  </div>

                  {/* ── Inline JD paste form ── */}
                  {state === 'adding' && (
                    <div className="email-jd-form">
                      <div className="email-jd-label">
                        Paste the full job description from {job.source === 'linkedin' ? 'LinkedIn' : 'Indeed'}
                      </div>
                      <textarea
                        className="paste-textarea"
                        rows={5}
                        placeholder={`Open "${job.title}" at ${job.company}, copy the full job description, and paste it here…`}
                        value={jdTexts[job.index] ?? ''}
                        onChange={e => setJdTexts(prev => ({ ...prev, [job.index]: e.target.value }))}
                        autoFocus
                      />
                      <div className="email-jd-actions">
                        <button
                          className="paste-submit"
                          onClick={() => saveJob(job)}
                          disabled={savingIdx === job.index || !jdTexts[job.index]?.trim()}
                        >
                          {savingIdx === job.index ? 'Saving…' : 'Save to My Jobs'}
                        </button>
                      </div>
                    </div>
                  )}
                </div>
              )
            })}
          </div>
        )}
      </div>
    </div>
  )
}
