import { useState, useRef, useEffect, useCallback } from 'react'
import type { KeyboardEvent } from 'react'
import GapMap from './components/GapMap'
import PastePanel from './components/PastePanel'
import JobsList from './components/JobsList'
import CareerRadar from './components/CareerRadar'
import WorkLogPanel from './components/WorkLogPanel'
import EmailJobsPanel from './components/EmailJobsPanel'
import NotifyPanel from './components/NotifyPanel'
import HistoryPanel from './components/HistoryPanel'
import MarkdownMessage from './components/MarkdownMessage'
import './App.css'

type PanelType = 'cv' | 'jd' | 'jobs' | 'worklog' | 'email' | 'notify' | 'history' | null

interface CareerRadarMessage {
  role: 'system'
  type: 'career_radar'
}

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

type Message = TextMessage | GapMessage | CareerRadarMessage

const TOOL_LABELS: Record<string, string> = {
  get_cv_skills: 'Reading CV skills',
  list_saved_jobs: 'Checking saved jobs',
  get_gap_analysis: 'Running gap analysis',
  get_career_pathfinder: 'Finding career paths',
  get_work_log_summary: 'Reviewing work log',
  get_job_details: 'Loading job details',
  get_email_job_alerts: 'Checking LinkedIn email alerts',
}

const WELCOME: TextMessage = {
  role: 'assistant',
  type: 'text',
  content:
    "Hi! I'm Career Radar — your AI career advisor for Singapore's job market.\n\nGet started by pasting your CV and a job description using the buttons above, then click \"Analyse Gap\" to see your personalised skills gap map.\n\nYou can also ask me questions like \"which job am I most ready for?\" and I'll analyse your data to answer.",
}

export default function App() {
  const [messages, setMessages] = useState<Message[]>([WELCOME])
  const [input, setInput] = useState('')
  const [streaming, setStreaming] = useState(false)
  const [panel, setPanel] = useState<PanelType>(null)
  const [selectedJobIds, setSelectedJobIds] = useState<number[]>([])
  const [addMenuOpen, setAddMenuOpen] = useState(false)
  const bottomRef = useRef<HTMLDivElement>(null)
  const addMenuRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    function handleClickOutside(e: MouseEvent) {
      if (addMenuRef.current && !addMenuRef.current.contains(e.target as Node)) {
        setAddMenuOpen(false)
      }
    }
    document.addEventListener('mousedown', handleClickOutside)
    return () => document.removeEventListener('mousedown', handleClickOutside)
  }, [])

  const openPanel = useCallback((p: PanelType) => {
    setPanel(p)
    setAddMenuOpen(false)
  }, [])

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

    // Add blank assistant message to fill in as chunks arrive
    setMessages([...history, { role: 'assistant', type: 'text', content: '' }])
    setInput('')
    setStreaming(true)

    const bufferedToolCalls: string[] = []
    let toolBreadcrumbInserted = false

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
            const event = JSON.parse(payload)

            if (event.type === 'tool_call') {
              bufferedToolCalls.push(TOOL_LABELS[event.tool] ?? event.tool)
              continue
            }

            if (event.type === 'error') {
              setMessages((prev) => {
                const updated = [...prev]
                const last = updated[updated.length - 1]
                if (last.type === 'text') {
                  updated[updated.length - 1] = {
                    ...last,
                    content: `⚠ ${event.message}`,
                    role: 'system' as const,
                  }
                }
                return updated
              })
              continue
            }

            if (event.text) {
              // Insert tool breadcrumb before first text chunk
              if (bufferedToolCalls.length > 0 && !toolBreadcrumbInserted) {
                toolBreadcrumbInserted = true
                const breadcrumb = bufferedToolCalls.join(' → ')
                setMessages((prev) => {
                  const updated = [...prev]
                  // Insert system message before the last (blank assistant) message
                  updated.splice(updated.length - 1, 0, {
                    role: 'system',
                    type: 'text',
                    content: `Using: ${breadcrumb}`,
                  })
                  return updated
                })
              }

              // Append text chunk to assistant message
              setMessages((prev) => {
                const updated = [...prev]
                const last = updated[updated.length - 1]
                if (last.type === 'text') {
                  updated[updated.length - 1] = {
                    ...last,
                    content: last.content + event.text,
                  }
                }
                return updated
              })
            }
          } catch {}
        }
      }
    } catch {
      setMessages((prev) => {
        const updated = [...prev]
        const last = updated[updated.length - 1]
        if (last.type === 'text') {
          updated[updated.length - 1] = {
            ...last,
            content: 'Something went wrong. Please try again.',
          }
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
        {/* Row 1: title + subtitle inline */}
        <div className="chat-header-title-row">
          <span className="chat-header-title">Career Radar</span>
          <span className="chat-header-sub">Skills gap advisor · SkillsFuture SG</span>
        </div>

        {/* Row 2: overview */}
        <div className="chat-header-overview">
          Career Radar helps you stay career-ready even when you're not actively applying for jobs. It integrates Singapore's SkillsFuture data with your CV, saved job alerts from your favorite job portals, and work logs to turn scattered signals into one explainable skills-gap view — so if a layoff happens or your goals shift, you already know where you stand and what to learn next.
        </div>

        {/* Rows 3–6: action buttons full-width */}
        <div className="header-btn-list">
          <div className="header-btn-row">
            <button className="action-btn header-btn" onClick={() => setPanel(panel === 'jobs' ? null : 'jobs')}>
              My Curated Shortlist
            </button>
            <span className="header-btn-desc">Jobs you handpicked — beyond what any algorithm decided for you.</span>
          </div>
          <div className="header-btn-row">
            <button className="action-btn header-btn" onClick={() => setMessages((prev) => [...prev, { role: 'system', type: 'career_radar' }])}>
              Skills Compass
            </button>
            <span className="header-btn-desc">Visualise how ready you are for each role. Discover which SkillsFuture career tracks fit your profile best.</span>
          </div>
          <div className="header-btn-row">
            <button className="action-btn action-btn-primary header-btn" onClick={analyseGap}>
              {selectedJobIds.length > 0 ? `Analyse (${selectedJobIds.length})` : 'Analyse Gap'}
            </button>
            <span className="header-btn-desc">See exactly which skills to build next, ranked by demand across your shortlisted jobs.</span>
          </div>
          <div className="header-btn-row">
            <button className="action-btn header-btn" onClick={() => openPanel(panel === 'history' ? null : 'history')}>
              Career History
            </button>
            <span className="header-btn-desc">Track how your job search and skills have evolved month by month since July 2025.</span>
          </div>
        </div>

        {/* Row 7: + Add dropdown */}
        <div className="add-dropdown" ref={addMenuRef}>
          <button
            className={`action-btn add-dropdown-trigger${addMenuOpen ? ' active' : ''}`}
            onClick={() => setAddMenuOpen((o) => !o)}
          >
            + Add ▾
          </button>
          {addMenuOpen && (
            <div className="add-dropdown-menu">
              <button className="add-dropdown-item add-dropdown-item--described" onClick={() => openPanel(panel === 'cv' ? null : 'cv')}>
                <span className="add-dropdown-item-label">My CV</span>
                <span className="add-dropdown-item-desc">Paste your résumé so the AI can map your existing skills and benchmark you against job requirements.</span>
              </button>
              <button className="add-dropdown-item add-dropdown-item--described" onClick={() => openPanel(panel === 'jd' ? null : 'jd')}>
                <span className="add-dropdown-item-label">Add Job</span>
                <span className="add-dropdown-item-desc">Paste a job description manually — from any job board or company site — to add it to your shortlist.</span>
              </button>
              <button className="add-dropdown-item add-dropdown-item--described" onClick={() => openPanel(panel === 'email' ? null : 'email')}>
                <span className="add-dropdown-item-label">Email Alerts</span>
                <span className="add-dropdown-item-desc">Jobs from your LinkedIn, Indeed &amp; Glassdoor alert emails — already filtered by their AI. Save only the ones that truly interest you.</span>
              </button>
              <button className="add-dropdown-item add-dropdown-item--described" onClick={() => openPanel(panel === 'worklog' ? null : 'worklog')}>
                <span className="add-dropdown-item-label">Work Log</span>
                <span className="add-dropdown-item-desc">Paste your recent work log or activity summary so the AI can extract your demonstrated skills and seniority signals.</span>
              </button>
              <button className="add-dropdown-item add-dropdown-item--described" onClick={() => openPanel(panel === 'notify' ? null : 'notify')}>
                <span className="add-dropdown-item-label">Job Search with Apify</span>
                <span className="add-dropdown-item-desc">Scrape fresh LinkedIn &amp; Indeed jobs matching your CV skills via Apify actors and get emailed a curated list.</span>
              </button>
            </div>
          )}
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
      {panel === 'email' && (
        <EmailJobsPanel
          onClose={() => setPanel(null)}
          onSaved={(msg: string) => {
            addSystemMsg(msg)
            setPanel(null)
          }}
        />
      )}
      {panel === 'worklog' && (
        <WorkLogPanel
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
          onDeleted={(msg) => {
            addSystemMsg(msg)
          }}
          selectedIds={selectedJobIds}
          onSelectionChange={setSelectedJobIds}
        />
      )}
      {panel === 'notify' && (
        <NotifyPanel
          onClose={() => setPanel(null)}
          onDone={(msg) => {
            addSystemMsg(msg)
            setPanel(null)
          }}
        />
      )}
      {panel === 'history' && (
        <HistoryPanel onClose={() => setPanel(null)} />
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
          if (msg.type === 'career_radar') {
            return (
              <div key={i} className="msg msg-gap">
                <CareerRadar />
              </div>
            )
          }
          // Tool breadcrumb styling
          if (msg.role === 'system' && msg.type === 'text' && msg.content.startsWith('Using:')) {
            return (
              <div key={i} className="msg msg-tool-activity">
                <span className="tool-activity-pill">{msg.content}</span>
              </div>
            )
          }
          return (
            <div key={i} className={`msg msg-${msg.role}`}>
              <div className="bubble">
                {msg.role === 'assistant' ? (
                  msg.content
                    ? <MarkdownMessage content={msg.content} isStreaming={streaming && i === messages.length - 1} />
                    : streaming && i === messages.length - 1 ? <span className="cursor" /> : null
                ) : (
                  msg.content
                    ? msg.content.split('\n').map((line, j) =>
                        line ? <p key={j}>{line}</p> : <br key={j} />
                      )
                    : null
                )}
              </div>
            </div>
          )
        })}
        <div ref={bottomRef} />
      </main>

      <footer className="chat-footer">
        <div className="chat-suggestions">
          {[
            'If I got laid off today, which jobs from my shortlist should I apply for first?',
            'What jobs should I prepare for if I want to quit next year?',
          ].map((q) => (
            <button
              key={q}
              className="suggestion-chip"
              disabled={streaming}
              onClick={() => setInput(q)}
            >
              {q}
            </button>
          ))}
        </div>
        <div className="chat-input-row">
          <textarea
            className="chat-input"
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={onKeyDown}
            placeholder="Ask anything — e.g. which job am I most ready for?"
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
        </div>
      </footer>
    </div>
  )
}
