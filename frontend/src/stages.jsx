import React, { useState } from 'react'
import { Card, SectionTitle, Badge, DataTable, MetricBox, EmptyState } from './components'

/* ── Stage 1: Extraction ──────────────────────────────────────── */
export function ExtractionPanel({ data }) {
  if (!data) return <EmptyState />
  return (
    <div>
      <DataTable rows={[
        ['Incident ID',  data.incident_id],
        ['Severity',     <Badge color="red">{data.severity}</Badge>],
        ['CI / CMDB',    <span>{data.ci_name} {data.ci_attached
          ? <Badge color="blue">CI attached</Badge>
          : <Badge color="amber">No CI</Badge>}
        </span>],
        ['Team',         data.team],
        ['Key actors',   data.key_actors?.join(', ') || '—'],
        ['Components',   data.affected_components?.join(', ') || '—'],
        ['Noise filtered', `${data.automated_entries_filtered} automated entries removed`],
      ]} />

      {data.human_notes?.length > 0 && (
        <div style={{ marginTop: 16 }}>
          <SectionTitle>Human work notes ({data.human_notes.length})</SectionTitle>
          <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: 12 }}>
            <thead>
              <tr style={{ background: 'var(--gray-50)' }}>
                <th style={{ padding: '6px 10px', textAlign: 'left', color: 'var(--gray-600)', fontWeight: 500, width: 110 }}>Time</th>
                <th style={{ padding: '6px 10px', textAlign: 'left', color: 'var(--gray-600)', fontWeight: 500 }}>Note</th>
              </tr>
            </thead>
            <tbody>
              {data.human_notes.map((n, i) => (
                <tr key={i} style={{ borderBottom: '1px solid var(--gray-100)' }}>
                  <td style={{ padding: '6px 10px', color: 'var(--gray-600)', whiteSpace: 'nowrap' }}>{n.time}</td>
                  <td style={{ padding: '6px 10px', color: 'var(--gray-800)' }}>{n.note}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  )
}

/* ── Stage 2: Timeline ────────────────────────────────────────── */
const catColor = {
  detection:     'var(--red-600)',
  investigation: 'var(--amber-600)',
  diagnosis:     'var(--blue-600)',
  fix:           'var(--teal-600)',
  recovery:      'var(--green-600)',
}
const catBg = {
  detection:     'var(--red-50)',
  investigation: 'var(--amber-50)',
  diagnosis:     'var(--blue-50)',
  fix:           'var(--teal-50)',
  recovery:      'var(--green-50)',
}

export function TimelinePanel({ data }) {
  if (!data) return <EmptyState />
  return (
    <div>
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(4,1fr)', gap: 10, marginBottom: 16 }}>
        <MetricBox value={data.mttr_minutes}            unit="m" label="MTTR" />
        <MetricBox value={data.time_to_detect_minutes}  unit="m" label="Time to detect" />
        <MetricBox value={data.time_to_diagnose_minutes}unit="m" label="Time to diagnose" />
        <MetricBox value={data.time_to_fix_minutes}     unit="m" label="Time to fix" />
      </div>

      {data.eureka_moment && (
        <div style={{
          background: 'var(--amber-50)', border: '1px solid var(--amber-200)',
          borderRadius: 'var(--radius-md)', padding: '10px 14px', marginBottom: 14,
        }}>
          <div style={{ fontSize: 11, fontWeight: 600, color: 'var(--amber-800)', textTransform: 'uppercase', letterSpacing: '0.4px' }}>
            ⚡ Eureka moment — {data.eureka_moment.time}
          </div>
          <div style={{ fontSize: 13, color: 'var(--amber-800)', marginTop: 3 }}>{data.eureka_moment.description}</div>
        </div>
      )}

      {data.narrative_summary && (
        <p style={{ fontSize: 13, color: 'var(--gray-600)', lineHeight: 1.7, marginBottom: 14 }}>
          {data.narrative_summary}
        </p>
      )}

      <div>
        {data.timeline?.map((ev, i) => (
          <div key={i} style={{ display: 'flex', gap: 12, padding: '7px 0', position: 'relative' }}>
            {i < data.timeline.length - 1 && (
              <div style={{ position: 'absolute', left: 14, top: 32, bottom: -4, width: 1, background: 'var(--gray-100)' }} />
            )}
            <div style={{
              width: 28, height: 28, borderRadius: '50%', flexShrink: 0, zIndex: 1,
              display: 'flex', alignItems: 'center', justifyContent: 'center',
              background: catBg[ev.category] || 'var(--gray-50)',
              color: catColor[ev.category] || 'var(--gray-600)',
              fontSize: 10, fontWeight: 700,
            }}>
              {ev.is_eureka ? '⚡' : ev.category?.slice(0, 2).toUpperCase()}
            </div>
            <div>
              <div style={{ fontSize: 13, fontWeight: 500, color: 'var(--gray-800)' }}>{ev.event}</div>
              <div style={{ fontSize: 11, color: 'var(--gray-600)', marginTop: 2 }}>
                {ev.time} · <span style={{ color: catColor[ev.category] }}>{ev.category}</span>
              </div>
            </div>
          </div>
        ))}
      </div>
    </div>
  )
}

/* ── Stage 3: Quality ─────────────────────────────────────────── */
const qualityColor = { high: 'var(--green-600)', medium: 'var(--amber-600)', low: 'var(--red-600)' }

export function QualityPanel({ data }) {
  if (!data) return <EmptyState />
  const qc = qualityColor[data.overall_quality] || 'var(--gray-600)'
  return (
    <div>
      <div style={{ display: 'flex', alignItems: 'center', gap: 14, marginBottom: 16 }}>
        <div style={{ fontSize: 36, fontWeight: 500, color: qc }}>{data.quality_score}</div>
        <div>
          <div style={{ fontSize: 14, fontWeight: 500, color: qc }}>
            {data.overall_quality?.charAt(0).toUpperCase() + data.overall_quality?.slice(1)} quality RCA
          </div>
          <div style={{ fontSize: 12, color: 'var(--gray-600)' }}>Score out of 100</div>
        </div>
      </div>

      <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
        {data.checks?.map((c, i) => {
          const bg = c.passed ? 'var(--green-50)' : c.severity === 'warn' ? 'var(--amber-50)' : 'var(--red-50)'
          const col = c.passed ? 'var(--green-600)' : c.severity === 'warn' ? 'var(--amber-600)' : 'var(--red-600)'
          return (
            <div key={i} style={{ background: bg, borderRadius: 'var(--radius-md)', padding: '10px 14px', display: 'flex', gap: 10 }}>
              <span style={{ color: col, fontSize: 14, flexShrink: 0 }}>{c.passed ? '✓' : c.severity === 'warn' ? '△' : '✗'}</span>
              <div>
                <div style={{ fontSize: 13, fontWeight: 500, color: col }}>{c.name}</div>
                <div style={{ fontSize: 12, color: 'var(--gray-600)', marginTop: 2 }}>{c.detail}</div>
              </div>
            </div>
          )
        })}
      </div>

      {data.recommendations?.length > 0 && (
        <div style={{ marginTop: 14 }}>
          <SectionTitle>Recommendations</SectionTitle>
          {data.recommendations.map((r, i) => (
            <div key={i} style={{ fontSize: 13, color: 'var(--gray-600)', padding: '4px 0', borderBottom: '1px solid var(--gray-100)' }}>
              → {r}
            </div>
          ))}
        </div>
      )}
    </div>
  )
}

/* ── Stage 4: Confluence ──────────────────────────────────────── */
export function ConfluencePanel({ data, incidentId }) {
  const [copied, setCopied] = useState(false)
  if (!data) return <EmptyState />

  const copyText = () => {
    const el = document.getElementById('conf-preview')
    if (el) {
      navigator.clipboard.writeText(el.innerText).then(() => {
        setCopied(true)
        setTimeout(() => setCopied(false), 2000)
      })
    }
  }

  return (
    <div>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 14 }}>
        <div>
          <div style={{ fontSize: 11, fontWeight: 600, color: 'var(--gray-600)', textTransform: 'uppercase', letterSpacing: '0.4px' }}>
            Confluence page ready
          </div>
          <div style={{ fontSize: 14, fontWeight: 500, marginTop: 2 }}>{data.page_title}</div>
        </div>
        <button
          onClick={copyText}
          style={{
            padding: '8px 16px', borderRadius: 'var(--radius-md)', fontSize: 13, fontWeight: 500,
            background: copied ? 'var(--green-600)' : 'var(--blue-600)', color: '#fff', border: 'none', cursor: 'pointer',
          }}
        >
          {copied ? 'Copied!' : 'Copy page'}
        </button>
      </div>

      <div id="conf-preview" style={{
        background: '#FAFAF8', border: '1px solid var(--gray-100)',
        borderRadius: 'var(--radius-md)', padding: 20,
        fontFamily: 'Georgia, serif',
      }}>
        <h2 style={{ fontSize: 18, color: '#172B4D', marginBottom: 14 }}>{data.page_title}</h2>

        {data.sections?.map((s, i) => (
          <div key={i}>
            <h3 style={{ fontSize: 14, fontWeight: 700, color: '#172B4D', margin: '14px 0 6px', borderBottom: '1px solid var(--gray-100)', paddingBottom: 4 }}>
              {s.heading}
            </h3>
            <p style={{ fontSize: 13, color: '#42526E', lineHeight: 1.7 }}>{s.content}</p>
          </div>
        ))}

        {data.action_items?.length > 0 && (
          <>
            <h3 style={{ fontSize: 14, fontWeight: 700, color: '#172B4D', margin: '14px 0 6px' }}>Action items</h3>
            <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: 12, fontFamily: 'var(--font)' }}>
              <thead>
                <tr style={{ background: 'var(--gray-50)' }}>
                  {['Owner','Task','Due'].map(h => (
                    <th key={h} style={{ padding: '6px 10px', textAlign: 'left', color: 'var(--gray-600)', fontWeight: 500 }}>{h}</th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {data.action_items.map((a, i) => (
                  <tr key={i} style={{ borderBottom: '1px solid var(--gray-100)' }}>
                    <td style={{ padding: '6px 10px' }}>{a.owner}</td>
                    <td style={{ padding: '6px 10px' }}>{a.task}</td>
                    <td style={{ padding: '6px 10px', whiteSpace: 'nowrap' }}>{a.due}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </>
        )}

        {data.tags?.length > 0 && (
          <div style={{ marginTop: 14 }}>
            {data.tags.map((t, i) => (
              <span key={i} style={{
                display: 'inline-block', margin: '3px 4px 3px 0',
                padding: '2px 8px', background: '#DFE1E6', borderRadius: 4,
                fontSize: 11, color: '#42526E', fontFamily: 'var(--font)',
              }}>{t}</span>
            ))}
          </div>
        )}
      </div>
    </div>
  )
}
