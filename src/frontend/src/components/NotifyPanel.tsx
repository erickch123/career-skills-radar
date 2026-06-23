import { useState } from 'react'

interface Props {
  onClose: () => void
  onDone: (msg: string) => void
}

type Tab = 'jobs' | 'gaps'

export default function NotifyPanel({ onClose, onDone }: Props) {
  const [tab, setTab]       = useState<Tab>('jobs')
  const [email, setEmail]   = useState('')
  const [loading, setLoading] = useState(false)
  const [result, setResult] = useState<null | { subject: string; mode: string; error?: string }>(null)

  async function trigger() {
    if (!email.trim()) return
    setLoading(true)
    setResult(null)
    try {
      const endpoint = tab === 'jobs' ? '/api/notify/jobs' : '/api/notify/gaps'
      const res = await fetch(endpoint, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ to_email: email, max_results: 5 }),
      })
      const data = await res.json()
      if (data.error) {
        setResult({ subject: '', mode: 'error', error: data.error })
        return
      }
      const n = data.notification
      setResult({ subject: n.subject, mode: n.mode, error: n.error })
      if (n.mode !== 'error') {
        const modeLabel = n.mode === 'live' ? 'Email sent' : 'Demo preview ready'
        onDone(`${modeLabel} — "${n.subject}"`)
        onClose()
      }
    } catch {
      setResult({ subject: '', mode: 'error', error: 'Request failed. Is the backend running?' })
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="paste-panel">
      <div className="paste-panel-header">
        <span>Job Alerts &amp; Notifications</span>
        <button className="paste-close" onClick={onClose}>✕</button>
      </div>

      <div className="notify-tabs">
        <button
          className={`notify-tab${tab === 'jobs' ? ' active' : ''}`}
          onClick={() => setTab('jobs')}
        >
          New Job Matches
        </button>
        <button
          className={`notify-tab${tab === 'gaps' ? ' active' : ''}`}
          onClick={() => setTab('gaps')}
        >
          Skill Gap Reminder
        </button>
      </div>

      <p className="notify-desc">
        {tab === 'jobs'
          ? 'Scrape fresh LinkedIn & Indeed listings matching your CV skills and email them to you.'
          : 'Send a summary of your top skill gaps — the skills most in demand that you haven\'t listed on your CV.'}
      </p>

      <input
        className="paste-meta-input notify-email-input"
        placeholder="Your email address"
        type="email"
        value={email}
        onChange={(e) => setEmail(e.target.value)}
      />

      {result?.error && (
        <div className="notify-error">{result.error}</div>
      )}

      <div className="paste-actions">
        <button
          className="paste-submit"
          onClick={trigger}
          disabled={loading || !email.trim()}
        >
          {loading ? 'Sending…' : tab === 'jobs' ? 'Find & Send Jobs' : 'Send Gap Reminder'}
        </button>
        <span className="notify-mode-hint">
          {!loading && 'No Apify/Resend keys? Runs in demo mode — shows a preview.'}
        </span>
      </div>
    </div>
  )
}
