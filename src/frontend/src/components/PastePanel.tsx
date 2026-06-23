import { useState } from 'react'

type PanelType = 'cv' | 'jd'

interface Props {
  type: PanelType
  onClose: () => void
  onSaved: (msg: string) => void
}

export default function PastePanel({ type, onClose, onSaved }: Props) {
  const [text, setText] = useState('')
  const [title, setTitle] = useState('')
  const [company, setCompany] = useState('')
  const [loading, setLoading] = useState(false)

  async function submit() {
    if (!text.trim()) return
    setLoading(true)
    try {
      if (type === 'cv') {
        const res = await fetch('/api/profile/cv', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ cv_text: text }),
        })
        const data = await res.json()
        onSaved(`CV saved — ${data.skills_found} skills identified.`)
      } else {
        const res = await fetch('/api/jobs', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ jd_text: text, title: title || null, company: company || null }),
        })
        const data = await res.json()
        onSaved(`Job saved — ${data.skills_found} skills identified.`)
      }
      onClose()
    } catch {
      onSaved('Something went wrong saving. Please try again.')
      onClose()
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="paste-panel">
      <div className="paste-panel-header">
        <span>{type === 'cv' ? 'Paste your CV' : 'Add job description'}</span>
        <button className="paste-close" onClick={onClose}>✕</button>
      </div>

      {type === 'jd' && (
        <div className="paste-meta-row">
          <input
            className="paste-meta-input"
            placeholder="Job title (optional)"
            value={title}
            onChange={(e) => setTitle(e.target.value)}
          />
          <input
            className="paste-meta-input"
            placeholder="Company (optional)"
            value={company}
            onChange={(e) => setCompany(e.target.value)}
          />
        </div>
      )}

      <textarea
        className="paste-textarea"
        placeholder={type === 'cv' ? 'Paste your full CV here…' : 'Paste the job description here…'}
        value={text}
        onChange={(e) => setText(e.target.value)}
        rows={10}
      />

      <div className="paste-actions">
        <button className="paste-submit" onClick={submit} disabled={loading || !text.trim()}>
          {loading ? 'Saving…' : 'Save & extract skills'}
        </button>
      </div>
    </div>
  )
}
