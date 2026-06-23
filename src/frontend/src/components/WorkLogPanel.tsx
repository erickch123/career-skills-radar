import { useState } from 'react'

interface Props {
  onClose: () => void
  onSaved: (msg: string) => void
}

export default function WorkLogPanel({ onClose, onSaved }: Props) {
  const [text, setText] = useState('')
  const [period, setPeriod] = useState('')
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')

  async function submit() {
    if (!text.trim()) return
    setLoading(true)
    setError('')
    try {
      const res = await fetch('/api/worklog', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ raw_text: text.trim(), period_covered: period.trim() || null }),
      })
      const data = await res.json()
      if (!res.ok) { setError(data.detail || 'Failed to save.'); return }
      onSaved(
        `Work log saved — ${data.skills_found} skills found` +
          (data.activities_summary ? `. ${data.activities_summary}` : '')
      )
    } catch {
      setError('Something went wrong. Please try again.')
    } finally {
      setLoading(false)
    }
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
