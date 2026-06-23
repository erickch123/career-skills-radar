import {
  BarChart, Bar, XAxis, YAxis, Tooltip, Cell, ResponsiveContainer,
} from 'recharts'

interface Gap {
  rank: number
  skill: string
  priority: number
  why: string
  demand_count: number
  total_jds: number
  is_emerging: boolean
  is_casl: boolean
}

interface Readiness {
  overall_pct: number
  per_jd: { jd_id: number; title: string; company: string; coverage_pct: number }[]
}

interface GapMapData {
  readiness: Readiness
  gaps: Gap[]
  cv_skills_count: number
  jobs_count: number
}

interface Props {
  data: GapMapData
}

function barColor(gap: Gap) {
  if (gap.is_casl) return '#ef4444'
  if (gap.is_emerging) return '#f97316'
  return '#2563eb'
}

export default function GapMap({ data }: Props) {
  const chartData = data.gaps.map((g) => ({
    ...g,
    label: g.skill.length > 28 ? g.skill.slice(0, 27) + '…' : g.skill,
    pct: Math.round(g.priority * 100),
  }))

  return (
    <div className="gap-map">
      <div className="gap-map-header">
        <div>
          <div className="gap-map-title">Career Skills Gap Analysis</div>
          <div className="gap-map-subtitle">Gaps ranked by demand across your saved jobs · skills mapped to SkillsFuture TSC framework</div>
        </div>
        <div className="gap-map-meta">
          {data.cv_skills_count} CV skills · {data.jobs_count} job{data.jobs_count !== 1 ? 's' : ''}
        </div>
      </div>

      <div className="readiness-row">
        <div className="readiness-score">{data.readiness.overall_pct}%</div>
        <div className="readiness-label">overall readiness</div>
        <div className="readiness-bar-bg">
          <div
            className="readiness-bar-fill"
            style={{ width: `${data.readiness.overall_pct}%` }}
          />
        </div>
      </div>

      <div className="gap-legend">
        <span className="dot dot-blue" /> Normal
        <span className="dot dot-orange" /> Emerging
        <span className="dot dot-red" /> CASL Priority
      </div>

      <ResponsiveContainer width="100%" height={Math.max(200, data.gaps.length * 32)}>
        <BarChart
          data={chartData}
          layout="vertical"
          margin={{ top: 0, right: 40, left: 8, bottom: 0 }}
        >
          <XAxis type="number" domain={[0, 1]} hide />
          <YAxis
            type="category"
            dataKey="label"
            width={180}
            tick={{ fontSize: 12, fill: 'var(--text-h)' }}
          />
          <Tooltip
            formatter={(_: unknown, __: unknown, props: { payload?: Gap }) =>
              props.payload ? [props.payload.why, ''] : []
            }
            contentStyle={{
              fontSize: 12,
              background: 'var(--bg-surface)',
              border: '1px solid var(--border)',
              borderRadius: 8,
              maxWidth: 280,
              whiteSpace: 'normal',
            }}
          />
          <Bar dataKey="priority" radius={[0, 4, 4, 0]}>
            {chartData.map((entry, i) => (
              <Cell key={i} fill={barColor(entry)} />
            ))}
          </Bar>
        </BarChart>
      </ResponsiveContainer>

      {data.readiness.per_jd.length > 1 && (
        <div className="per-jd">
          {data.readiness.per_jd.map((j) => (
            <div key={j.jd_id} className="per-jd-row">
              <span className="per-jd-title">{j.title}{j.company ? ` · ${j.company}` : ''}</span>
              <span className="per-jd-pct">{j.coverage_pct}%</span>
            </div>
          ))}
        </div>
      )}
    </div>
  )
}
