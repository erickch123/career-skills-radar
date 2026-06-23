import { useState, useEffect } from 'react'

interface Job {
  id: number
  title: string
  company: string
  skills_count: number
  date_saved: string | null
  raw_jd_text: string
}

interface Props {
  onClose: () => void
  onDeleted: (msg: string) => void
  selectedIds: number[]
  onSelectionChange: (ids: number[]) => void
}

export default function JobsList({ onClose, onDeleted, selectedIds, onSelectionChange }: Props) {
  const [jobs, setJobs] = useState<Job[]>([])
  const [loading, setLoading] = useState(true)
  const [viewingJD, setViewingJD] = useState<Job | null>(null)

  useEffect(() => {
    fetch('/api/jobs')
      .then((r) => r.json())
      .then((data) => { setJobs(data); setLoading(false) })
      .catch(() => setLoading(false))
  }, [])

  function toggleJob(id: number) {
    onSelectionChange(
      selectedIds.includes(id)
        ? selectedIds.filter((x) => x !== id)
        : [...selectedIds, id]
    )
  }

  function selectAll() {
    onSelectionChange(jobs.map((j) => j.id))
  }

  function clearAll() {
    onSelectionChange([])
  }

  async function deleteJob(id: number) {
    await fetch(`/api/jobs/${id}`, { method: 'DELETE' })
    setJobs((prev) => prev.filter((j) => j.id !== id))
    onSelectionChange(selectedIds.filter((x) => x !== id))
    onDeleted('Job removed.')
  }

  if (viewingJD) {
    return (
      <div className="paste-panel">
        <div className="paste-panel-header">
          <span>{viewingJD.title}{viewingJD.company ? ` · ${viewingJD.company}` : ''}</span>
          <button className="paste-close" onClick={() => setViewingJD(null)}>← Back</button>
        </div>
        <div className="jd-viewer">{viewingJD.raw_jd_text}</div>
      </div>
    )
  }

  return (
    <div className="paste-panel">
      <div className="paste-panel-header">
        <span>Saved Jobs ({jobs.length})</span>
        <div style={{ display: 'flex', gap: 8, alignItems: 'center' }}>
          {jobs.length > 0 && (
            <>
              <button className="jobs-select-btn" onClick={selectAll}>All</button>
              <button className="jobs-select-btn" onClick={clearAll}>None</button>
            </>
          )}
          <button className="paste-close" onClick={onClose}>✕</button>
        </div>
      </div>

      {selectedIds.length > 0 && (
        <div className="jobs-selection-hint">
          {selectedIds.length} job{selectedIds.length !== 1 ? 's' : ''} selected — click "Analyse Gap" to run targeted analysis
        </div>
      )}

      {loading && <div className="jobs-empty">Loading…</div>}
      {!loading && jobs.length === 0 && (
        <div className="jobs-empty">No jobs saved yet. Click "Add Job" to get started.</div>
      )}

      <div className="jobs-list">
        {jobs.map((job) => {
          const checked = selectedIds.includes(job.id)
          return (
            <div
              key={job.id}
              className={`job-row ${checked ? 'job-row-selected' : ''}`}
              onClick={() => toggleJob(job.id)}
            >
              <input
                type="checkbox"
                className="job-checkbox"
                checked={checked}
                onChange={() => toggleJob(job.id)}
                onClick={(e) => e.stopPropagation()}
              />
              <div className="job-info">
                <div className="job-title">{job.title}</div>
                <div className="job-meta">
                  {job.company && <span>{job.company} · </span>}
                  <span>{job.skills_count} skills</span>
                </div>
              </div>
              <div className="job-actions">
                <button
                  className="job-view"
                  onClick={(e) => { e.stopPropagation(); setViewingJD(job) }}
                >
                  View
                </button>
                <button
                  className="job-delete"
                  onClick={(e) => { e.stopPropagation(); deleteJob(job.id) }}
                >
                  ✕
                </button>
              </div>
            </div>
          )
        })}
      </div>
    </div>
  )
}
