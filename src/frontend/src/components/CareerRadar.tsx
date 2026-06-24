import { useState, useEffect } from 'react'
import {
  BarChart, Bar, XAxis, YAxis, Tooltip, Cell,
  ResponsiveContainer,
} from 'recharts'

interface TierEntry { tier: string; label: string; count: number }
interface JobEntry  { id: number; title: string; company: string; tier: string }
interface Role      { job_role: string; sector: string; overlap_count: number; total_required: number; match_pct: number }

interface ClassifyData {
  newly_classified: number
  distribution: TierEntry[]
  jobs: JobEntry[]
}

interface PathfinderData {
  cv_skills_count: number
  roles: Role[]
  error?: string
}

const TIER_COLORS: Record<string, string> = {
  entry: '#6ee7b7',
  mid: '#60a5fa',
  senior: '#818cf8',
  staff_principal: '#c084fc',
  manager_plus: '#f472b6',
}

export default function CareerRadar() {
  const [classify, setClassify] = useState<ClassifyData | null>(null)
  const [pathfinder, setPathfinder] = useState<PathfinderData | null>(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    async function load() {
      const [c, p] = await Promise.all([
        fetch('/api/insights/classify', { method: 'POST' }).then(r => r.json()),
        fetch('/api/insights/pathfinder').then(r => r.json()),
      ])
      setClassify(c)
      setPathfinder(p)
      setLoading(false)
    }
    load()
  }, [])

  if (loading) return <div className="radar-loading">Classifying jobs and building your career map…</div>

  return (
    <div className="career-radar">
      <div className="radar-title">Career Radar</div>
      <div className="radar-intro">
        See how your shortlisted jobs are distributed by seniority level, and discover which SkillsFuture career tracks your current skillset aligns with most.
        Use this to decide whether to aim higher, pivot sideways, or double down on your strongest track.
      </div>

      {/* ── Seniority Distribution ── */}
      {classify && classify.distribution.length > 0 && (
        <div className="radar-section">
          <div className="radar-section-title">
            Target Role Seniority
            <span className="radar-section-sub">{classify.jobs.length} jobs classified</span>
          </div>
          <ResponsiveContainer width="100%" height={160}>
            <BarChart data={classify.distribution} margin={{ top: 4, right: 16, left: 0, bottom: 0 }}>
              <XAxis dataKey="label" tick={{ fontSize: 11, fill: 'var(--text)' }} />
              <YAxis allowDecimals={false} tick={{ fontSize: 11, fill: 'var(--text)' }} width={20} />
              <Tooltip
                formatter={(v) => [`${v} job${v !== 1 ? 's' : ''}`, 'Count']}
                contentStyle={{ fontSize: 12, background: 'var(--bg-surface)', border: '1px solid var(--border)', borderRadius: 8 }}
              />
              <Bar dataKey="count" radius={[4, 4, 0, 0]}>
                {classify.distribution.map((entry, i) => (
                  <Cell key={i} fill={TIER_COLORS[entry.tier] ?? '#60a5fa'} />
                ))}
              </Bar>
            </BarChart>
          </ResponsiveContainer>

          <div className="radar-job-pills">
            {classify.jobs.map(j => (
              <span key={j.id} className="radar-pill" style={{ borderColor: TIER_COLORS[j.tier] ?? '#60a5fa' }}>
                {j.title}
                <span className="radar-pill-tier" style={{ color: TIER_COLORS[j.tier] ?? '#60a5fa' }}>
                  {j.tier?.replace('_', ' ')}
                </span>
              </span>
            ))}
          </div>
        </div>
      )}

      {/* ── Career Pathfinder ── */}
      {pathfinder && !pathfinder.error && pathfinder.roles.length > 0 && (
        <div className="radar-section">
          <div className="radar-section-title">
            Career Pathfinder
            <span className="radar-section-sub">closest SkillsFuture roles · {pathfinder.cv_skills_count} CV skills</span>
          </div>
          <ResponsiveContainer width="100%" height={Math.max(180, pathfinder.roles.length * 30)}>
            <BarChart
              data={pathfinder.roles.map(r => ({
                ...r,
                label: r.job_role.length > 32 ? r.job_role.slice(0, 31) + '…' : r.job_role,
              }))}
              layout="vertical"
              margin={{ top: 0, right: 40, left: 8, bottom: 0 }}
            >
              <XAxis type="number" domain={[0, 100]} tickFormatter={v => `${v}%`} tick={{ fontSize: 11, fill: 'var(--text)' }} />
              <YAxis type="category" dataKey="label" width={180} tick={{ fontSize: 11, fill: 'var(--text-h)' }} />
              <Tooltip
                formatter={(v, _name, props) => {
                  const p = props?.payload as Role | undefined
                  return p
                    ? [`${p.overlap_count} of ${p.total_required} skills matched (${v}%)`, '']
                    : [v, '']
                }}
                contentStyle={{ fontSize: 12, background: 'var(--bg-surface)', border: '1px solid var(--border)', borderRadius: 8 }}
              />
              <Bar dataKey="match_pct" radius={[0, 4, 4, 0]} fill="var(--accent)" />
            </BarChart>
          </ResponsiveContainer>
        </div>
      )}

      {pathfinder?.error && (
        <div className="radar-error">⚠ {pathfinder.error}</div>
      )}
    </div>
  )
}
