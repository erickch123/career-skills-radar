import { useState } from 'react'

interface Props {
  onClose: () => void
  onSaved: (msg: string) => void
}

interface SaveResult {
  skills_found: number
  skills: string[]
  new_skills_not_in_cv: string[]
  activities_summary?: string
}

export default function WorkLogPanel({ onClose, onSaved }: Props) {
  const [text, setText] = useState('')
  const [period, setPeriod] = useState('')
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')
  const [result, setResult] = useState<SaveResult | null>(null)
  const [addingToCV, setAddingToCV] = useState(false)
  const [cvAdded, setCvAdded] = useState(false)

  async function submit() {
    if (!text.trim()) return
    setLoading(true)
    setError('')
    setResult(null)
    setCvAdded(false)
    try {
      const res = await fetch('/api/worklog', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ raw_text: text.trim(), period_covered: period.trim() || null }),
      })
      const data = await res.json()
      if (!res.ok) { setError(data.detail || 'Failed to save.'); return }
      setResult(data)
    } catch {
      setError('Something went wrong. Please try again.')
    } finally {
      setLoading(false)
    }
  }

  async function addToCV() {
    if (!result?.new_skills_not_in_cv.length) return
    setAddingToCV(true)
    try {
      await fetch('/api/profile/cv-append', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ skills_to_add: result.new_skills_not_in_cv }),
      })
      setCvAdded(true)
      onSaved(
        `Work log saved — ${result.skills_found} skills found. ` +
        `${result.new_skills_not_in_cv.length} new skills added to your CV.`
      )
    } catch {
      setError('Failed to update CV.')
    } finally {
      setAddingToCV(false)
    }
  }

  function dismiss() {
    const msg = result
      ? `Work log saved — ${result.skills_found} skill${result.skills_found !== 1 ? 's' : ''} found` +
        (result.activities_summary ? `. ${result.activities_summary}` : '')
      : 'Work log saved.'
    onSaved(msg)
  }

  if (result) {
    return (
      <div className="paste-panel">
        <div className="paste-panel-header">
          <span>Work Log Saved</span>
          <button className="paste-close" onClick={dismiss}>✕</button>
        </div>

        <div className="worklog-result">
          {result.activities_summary && (
            <p className="worklog-result-summary">{result.activities_summary}</p>
          )}

          {result.skills_found > 0 ? (
            <div className="worklog-result-skills">
              <span className="worklog-result-label">Skills detected:</span>
              <div className="worklog-skill-pills">
                {result.skills.map(s => (
                  <span key={s} className="worklog-skill-pill">{s}</span>
                ))}
              </div>
            </div>
          ) : (
            <p className="worklog-result-none">No SkillsFuture-mapped skills detected in this entry.</p>
          )}

          {result.new_skills_not_in_cv.length > 0 && !cvAdded && (
            <div className="worklog-cv-suggestion">
              <div className="worklog-cv-suggestion-title">
                💡 {result.new_skills_not_in_cv.length} new skill{result.new_skills_not_in_cv.length !== 1 ? 's' : ''} not in your CV yet
              </div>
              <div className="worklog-skill-pills">
                {result.new_skills_not_in_cv.map(s => (
                  <span key={s} className="worklog-skill-pill worklog-skill-pill--new">{s}</span>
                ))}
              </div>
              <button
                className="paste-submit worklog-cv-btn"
                onClick={addToCV}
                disabled={addingToCV}
              >
                {addingToCV ? 'Adding…' : 'Add to my CV →'}
              </button>
            </div>
          )}

          {cvAdded && (
            <div className="worklog-cv-added">
              CV updated — skills appended and re-indexed.
            </div>
          )}
        </div>

        <div className="paste-actions">
          <button className="paste-submit" onClick={dismiss}>Done</button>
        </div>
      </div>
    )
  }

  return (
    <div className="paste-panel">
      <div className="paste-panel-header">
        <span>Add Work Log Entry</span>
        <button className="paste-close" onClick={onClose}>✕</button>
      </div>
      <div className="paste-meta-row">
        <input
          className="paste-meta-input"
          placeholder="Period covered (e.g. Jun 2025, Q2 2025)"
          value={period}
          onChange={e => setPeriod(e.target.value)}
        />
      </div>
      <textarea
        className="paste-textarea"
        rows={6}
        placeholder="Paste your work log, weekly update, or activity summary here…"
        value={text}
        onChange={e => setText(e.target.value)}
      />
      {error && <div style={{ color: '#ef4444', fontSize: 12, marginTop: 6 }}>{error}</div>}
      <div className="paste-actions">
        <button
          className="paste-submit"
          onClick={submit}
          disabled={loading || !text.trim()}
        >
          {loading ? 'Saving…' : 'Save Entry'}
        </button>
      </div>
    </div>
  )
}
