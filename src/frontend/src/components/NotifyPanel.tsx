import { useState } from 'react'

interface ApifyJob {
  title: string
  company: string
  location: string
  snippet: string
  job_url: string
  posted_at: string
  source: 'linkedin' | 'indeed'
  already_saved: boolean
}

type RowState = 'idle' | 'saving' | 'saved'

interface Props {
  onClose: () => void
  onDone: (msg: string) => void
}

export default function NotifyPanel({ onClose, onDone }: Props) {
  const [keywords, setKeywords] = useState('')
  const [jobs, setJobs] = useState<ApifyJob[]>([])
  const [keywordsUsed, setKeywordsUsed] = useState<string[]>([])
  const [mode, setMode] = useState<'live' | 'demo'>('demo')
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')
  const [rowStates, setRowStates] = useState<Record<string, RowState>>({})
  const [searched, setSearched] = useState(false)

  async function search() {
    setLoading(true)
    setError('')
    setJobs([])
    setRowStates({})
    try {
      const params = keywords.trim() ? `?keywords=${encodeURIComponent(keywords.trim())}` : ''
      const res = await fetch(`/api/apify/search${params}`)
      const data = await res.json()
      if (data.error) { setError(data.error); return }
      setJobs(data.jobs || [])
      setKeywordsUsed(data.keywords_used || [])
      setMode(data.mode)
      setSearched(true)
    } catch {
      setError('Search failed. Is the backend running?')
    } finally {
      setLoading(false)
    }
  }

  async function addToShortlist(job: ApifyJob) {
    const key = `${job.title}|${job.company}`
    setRowStates(prev => ({ ...prev, [key]: 'saving' }))
    try {
      const res = await fetch('/api/jobs', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          title: job.title,
          company: job.company,
          jd_text: job.snippet || `${job.title} at ${job.company} in ${job.location}`,
        }),
      })
      const data = await res.json()
      if (!res.ok) {
        setError(data.detail || 'Failed to save.')
        setRowStates(prev => ({ ...prev, [key]: 'idle' }))
        return
      }
      setRowStates(prev => ({ ...prev, [key]: 'saved' }))
      onDone(`${job.title} at ${job.company} added — ${data.skills_found} skills found`)
    } catch {
      setError('Save failed.')
      setRowStates(prev => ({ ...prev, [key]: 'idle' }))
    }
  }

  const linkedinJobs = jobs.filter(j => j.source === 'linkedin')
  const indeedJobs   = jobs.filter(j => j.source === 'indeed')

  return (
    <div className="email-overlay">
      {/* Header */}
      <div className="email-overlay-header">
        <span className="email-overlay-title">
          Job Search with Apify
          <span className={`email-source-badge${mode === 'live' ? ' email-source-live' : ''}`}>
            {mode === 'live' ? 'live' : 'demo data'}
          </span>
          {searched && jobs.length > 0 && (
            <span className="email-count">
              {linkedinJobs.length} LinkedIn · {indeedJobs.length} Indeed
            </span>
          )}
        </span>
        <button className="paste-close" onClick={onClose}>✕</button>
      </div>

      {/* Body */}
      <div className="email-overlay-body">
        <div className="apify-search-row">
          <input
            className="apify-search-input"
            placeholder="Keywords (e.g. Python data engineer) — leave blank to use your CV skills"
            value={keywords}
            onChange={e => setKeywords(e.target.value)}
            onKeyDown={e => e.key === 'Enter' && !loading && search()}
            disabled={loading}
          />
          <button
            className="paste-submit apify-search-btn"
            onClick={search}
            disabled={loading}
          >
            {loading ? 'Searching…' : 'Search'}
          </button>
        </div>

        {searched && keywordsUsed.length > 0 && (
          <div className="apify-keywords-used">
            Searched: {keywordsUsed.join(' · ')}
          </div>
        )}

        {error && <div className="email-error">{error}</div>}

        {!loading && searched && jobs.length === 0 && (
          <div className="jobs-empty">No jobs found. Try different keywords.</div>
        )}

        {jobs.length > 0 && (
          <div className="email-jobs-list">
            {jobs.map(job => {
              const key = `${job.title}|${job.company}`
              const state = rowStates[key] ?? (job.already_saved ? 'saved' : 'idle')
              return (
                <div key={key} className="email-job-card">
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
                        {job.posted_at && ` · ${job.posted_at}`}
                      </div>
                      {job.snippet && (
                        <div className="apify-snippet">{job.snippet}</div>
                      )}
                    </div>
                    <div className="email-job-actions">
                      {job.job_url && (
                        <a
                          href={job.job_url}
                          target="_blank"
                          rel="noopener noreferrer"
                          className="job-view"
                        >
                          View
                        </a>
                      )}
                      {state === 'saved' && (
                        <span className="email-job-tag">saved ✓</span>
                      )}
                      {state === 'saving' && (
                        <span className="email-job-tag">saving…</span>
                      )}
                      {state === 'idle' && (
                        <button
                          className="email-add-btn"
                          onClick={() => addToShortlist(job)}
                        >
                          + Add
                        </button>
                      )}
                    </div>
                  </div>
                </div>
              )
            })}
          </div>
        )}
      </div>
    </div>
  )
}
