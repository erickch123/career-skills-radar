import { useState, useRef, useEffect, KeyboardEvent } from 'react'
import GapMap from './components/GapMap'
import PastePanel from './components/PastePanel'
import JobsList from './components/JobsList'
import './App.css'

type PanelType = 'cv' | 'jd' | 'jobs' | null

interface TextMessage {
  role: 'user' | 'assistant' | 'system'
  type: 'text'
  content: string
}

interface GapMessage {
  role: 'system'
  type: 'gap_map'
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  data: any
}

type Message = TextMessage | GapMessage

const WELCOME: TextMessage = {
  role: 'assistant',
  type: 'text',
  content:
    "Hi! I'm Career Radar — your AI career advisor for Singapore's job market.\n\nGet started by pasting your CV and a job description using the buttons above, then click \"Analyse Gap\" to see your personalised skills gap map.",
}

export default function App() {
  const [messages, setMessages] = useState<Message[]>([WELCOME])
  const [input, setInput] = useState('')
  const [streaming, setStreaming] = useState(false)
  const [panel, setPanel] = useState<PanelType>(null)
  const [selectedJobIds, setSelectedJobIds] = useState<number[]>([])
  const bottomRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages])

  function addSystemMsg(content: string) {
    setMessages((prev) => [...prev, { role: 'system', type: 'text', content }])
  }

  async function analyseGap() {
    const label = selectedJobIds.length
      ? `Analysing gap against ${selectedJobIds.length} selected job${selectedJobIds.length !== 1 ? 's' : ''}…`
      : 'Analysing gap across all saved jobs…'
    addSystemMsg(label)
    try {
      const params = selectedJobIds.length
        ? '?' + selectedJobIds.map((id) => `job_ids=${id}`).join('&')
        : ''
      const res = await fetch(`/api/gap${params}`)
      const data = await res.json()
      if (data.error) {
        addSystemMsg(`⚠ ${data.error}`)
        return
      }
      setMessages((prev) => [...prev, { role: 'system', type: 'gap_map', data }])
    } catch {
      addSystemMsg('Failed to load gap analysis. Please try again.')
    }
  }

  async function send() {
    const text = input.trim()
    if (!text || streaming) return

    const userMsg: TextMessage = { role: 'user', type: 'text', content: text }
    const history = [...messages, userMsg]
    setMessages([...history, { role: 'assistant', type: 'text', content: '' }])
    setInput('')
    setStreaming(true)

    try {
      const res = await fetch('/api/chat', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          messages: history
            .filter((m): m is TextMessage => m.type === 'text' && m.role !== 'system')
            .map((m) => ({ role: m.role, content: m.content })),
        }),
      })

      if (!res.body) throw new Error('No response body')
      const reader = res.body.getReader()
      const decoder = new TextDecoder()

      while (true) {
        const { done, value } = await reader.read()
        if (done) break
        for (const line of decoder.decode(value).split('\n')) {
          if (!line.startsWith('data: ')) continue
          const payload = line.slice(6)
          if (payload === '[DONE]') break
          try {
            const { text: chunk } = JSON.parse(payload)
            setMessages((prev) => {
              const updated = [...prev]
              const last = updated[updated.length - 1]
              if (last.type === 'text') {
                updated[updated.length - 1] = { ...last, content: last.content + chunk }
              }
              return updated
            })
          } catch {}
        }
      }
    } catch {
      setMessages((prev) => {
        const updated = [...prev]
        const last = updated[updated.length - 1]
        if (last.type === 'text') {
          updated[updated.length - 1] = { ...last, content: 'Something went wrong. Please try again.' }
        }
        return updated
      })
    } finally {
      setStreaming(false)
    }
  }

  function onKeyDown(e: KeyboardEvent<HTMLTextAreaElement>) {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      send()
    }
  }

  return (
    <div className="chat-app">
      <header className="chat-header">
        <div className="chat-header-left">
          <div className="chat-header-title">Career Radar</div>
          <div className="chat-header-sub">Skills gap advisor · SkillsFuture SG</div>
        </div>
        <div className="chat-header-actions">
          <button
            className="action-btn"
            onClick={() => setPanel(panel === 'cv' ? null : 'cv')}
          >
            My CV
          </button>
          <button
            className="action-btn"
            onClick={() => setPanel(panel === 'jd' ? null : 'jd')}
          >
            Add Job
          </button>
          <button
            className="action-btn"
            onClick={() => setPanel(panel === 'jobs' ? null : 'jobs')}
          >
            Saved Jobs
          </button>
          <button className="action-btn action-btn-primary" onClick={analyseGap}>
            {selectedJobIds.length > 0 ? `Analyse (${selectedJobIds.length})` : 'Analyse Gap'}
          </button>
        </div>
      </header>

      {(panel === 'cv' || panel === 'jd') && (
        <PastePanel
          type={panel}
          onClose={() => setPanel(null)}
          onSaved={(msg) => {
            addSystemMsg(msg)
            setPanel(null)
          }}
        />
      )}
      {panel === 'jobs' && (
        <JobsList
          onClose={() => setPanel(null)}
          onDeleted={(msg) => { addSystemMsg(msg) }}
          selectedIds={selectedJobIds}
          onSelectionChange={setSelectedJobIds}
        />
      )}

      <main className="chat-messages">
        {messages.map((msg, i) => {
          if (msg.type === 'gap_map') {
            return (
              <div key={i} className="msg msg-gap">
                <GapMap data={msg.data} />
              </div>
            )
          }
          return (
            <div key={i} className={`msg msg-${msg.role}`}>
              <div className="bubble">
                {msg.content
                  ? msg.content.split('\n').map((line, j) =>
                      line ? <p key={j}>{line}</p> : <br key={j} />
                    )
                  : streaming && i === messages.length - 1
                    ? <span className="cursor" />
                    : null}
              </div>
            </div>
          )
        })}
        <div ref={bottomRef} />
      </main>

      <footer className="chat-footer">
        <textarea
          className="chat-input"
          value={input}
          onChange={(e) => setInput(e.target.value)}
          onKeyDown={onKeyDown}
          placeholder="Ask a question about your career, skills, or the gap map…"
          rows={3}
          disabled={streaming}
        />
        <button
          className="chat-send"
          onClick={send}
          disabled={streaming || !input.trim()}
        >
          {streaming ? '…' : 'Send'}
        </button>
      </footer>
    </div>
  )
}
