import { useState, useEffect } from 'react'
import {
  ComposedChart, Bar, Line, XAxis, YAxis, Tooltip,
  ResponsiveContainer, CartesianGrid, Legend,
} from 'recharts'

interface MonthBucket {
  month: string
  year_month: string
  jobs_saved: number
  work_logs: number
}

interface ActivityItem {
  type: 'job' | 'worklog'
  date: string
  label: string
  meta: string
}

interface TimelineData {
  months: MonthBucket[]
  total_jobs: number
  total_work_logs: number
  active_months: number
  recent: ActivityItem[]
}

interface Props {
  onClose: () => void
}

function relativeDate(iso: string): string {
  const diff = Date.now() - new Date(iso).getTime()
  const days = Math.floor(diff / 86400000)
  if (days === 0) return 'today'
  if (days === 1) return 'yesterday'
  if (days < 7) return `${days}d ago`
  if (days < 30) return `${Math.floor(days / 7)}w ago`
  if (days < 365) return `${Math.floor(days / 30)}mo ago`
  return `${Math.floor(days / 365)}y ago`
}

export default function HistoryPanel({ onClose }: Props) {
  const [data, setData] = useState<TimelineData | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')

  useEffect(() => {
    fetch('/api/timeline')
      .then(r => r.json())
      .then(d => { setData(d); setLoading(false) })
      .catch(() => { setError('Could not load timeline.'); setLoading(false) })
  }, [])

  return (
    <div className="paste-panel history-panel">
      <div className="paste-panel-header">
        <span>Career History</span>
        <button className="paste-close" onClick={onClose}>✕</button>
      </div>

      {loading && <div className="history-loading">Loading your timeline…</div>}
      {error && <div className="notify-error">{error}</div>}

      {data && (
        <>
          <div className="history-stats">
            <div className="history-stat">
              <span className="history-stat-num">{data.total_jobs}</span>
              <span className="history-stat-label">jobs saved</span>
            </div>
            <div className="history-stat">
              <span className="history-stat-num">{data.total_work_logs}</span>
              <span className="history-stat-label">work logs</span>
            </div>
            <div className="history-stat">
              <span className="history-stat-num">{data.active_months}</span>
              <span className="history-stat-label">months tracked</span>
            </div>
          </div>

          {data.months.length > 0 && (
            <div className="history-chart-wrap">
              <div className="history-chart-title">Monthly Activity</div>
              <ResponsiveContainer width="100%" height={200}>
                <ComposedChart data={data.months} margin={{ top: 4, right: 16, left: 0, bottom: 0 }}>
                  <CartesianGrid strokeDasharray="3 3" stroke="var(--border)" vertical={false} />
                  <XAxis
                    dataKey="month"
                    tick={{ fontSize: 10, fill: 'var(--text)' }}
                    interval={data.months.length > 8 ? 1 : 0}
                  />
                  <YAxis allowDecimals={false} tick={{ fontSize: 10, fill: 'var(--text)' }} width={22} />
                  <Tooltip
                    contentStyle={{
                      fontSize: 12,
                      background: 'var(--bg-surface)',
                      border: '1px solid var(--border)',
                      borderRadius: 8,
                    }}
                  />
                  <Legend
                    iconType="circle"
                    iconSize={8}
                    wrapperStyle={{ fontSize: 11, paddingTop: 6 }}
                  />
                  <Bar dataKey="jobs_saved" name="Jobs saved" fill="var(--accent)" radius={[3, 3, 0, 0]} />
                  <Line
                    type="monotone"
                    dataKey="work_logs"
                    name="Work logs"
                    stroke="#f59f00"
                    strokeWidth={2}
                    dot={{ r: 3, fill: '#f59f00' }}
                  />
                </ComposedChart>
              </ResponsiveContainer>
            </div>
          )}

          {data.recent.length > 0 && (
            <div className="history-feed">
              <div className="history-chart-title">Recent Activity</div>
              {data.recent.map((item, i) => (
                <div key={i} className={`history-feed-item history-feed-item--${item.type}`}>
                  <span className="history-feed-icon">
                    {item.type === 'job' ? '💼' : '📝'}
                  </span>
                  <div className="history-feed-body">
                    <span className="history-feed-label">{item.label}</span>
                    {item.meta && (
                      <span className="history-feed-meta">{item.meta.replace('_', ' ')}</span>
                    )}
                  </div>
                  <span className="history-feed-date">{relativeDate(item.date)}</span>
                </div>
              ))}
            </div>
          )}
        </>
      )}
    </div>
  )
}
