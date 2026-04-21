import React, { useState } from 'react'
import { runFullRCA } from './api'
import {
  Card, SectionTitle, Btn, FormField, Input, Textarea, Select,
  StatusPill, Spinner,
} from './components'
import { ExtractionPanel, TimelinePanel, QualityPanel, ConfluencePanel } from './stages'

const SAMPLE = {
  incident_id: 'INC0091847',
  severity: 'SEV2 - Major',
  ci: 'payments-api (CMDB: CI-00291)',
  opened_at: '2025-06-14 02:17 UTC',
  closed_at: '2025-06-14 05:44 UTC',
  team: 'Platform Reliability Engineering',
  work_notes: `02:17 - Alert fired: payment gateway timeout rate > 15%
02:21 - On-call engineer paged (Arjun S.)
02:34 - Arjun acknowledged. Checked dashboards — high error rate on payments-api pods.
02:55 - Suspected DB connection pool exhaustion. Increased pool size. No improvement.
03:12 - AUTOMATED: health check retry policy triggered
03:28 - Ravi joined. Reviewed recent deploys. Noted config change at 01:55 UTC reduced max_connections for payments-api from 200 to 20.
03:31 - Config rollback initiated on payments-api.
03:44 - Error rates returning to normal. Payment success rate recovering.
04:02 - AUTOMATED: alert resolved by monitoring system
05:44 - Incident formally closed. Post-mortem scheduled.`,
  resolution_notes: `Root cause identified as a misconfigured max_connections value in payments-api config deployed at 01:55 UTC. A routine config update incorrectly set the DB connection pool limit to 20 (down from 200), causing exhaustion under normal load. Rolled back config at 03:31 UTC. Recovery confirmed at 03:44 UTC. Future prevention: add config validation step in CI/CD pipeline to flag anomalous connection pool values.`,
}

const STAGES = [
  { key: 'extraction', label: 'Data extraction',    sub: 'ServiceNow · filter noise',      dot: 'var(--blue-600)'   },
  { key: 'timeline',   label: 'Timeline & analysis', sub: 'MTTR · Eureka moment',           dot: 'var(--teal-600)'   },
  { key: 'quality',    label: 'Quality validation',  sub: 'CI check · score 0–100',         dot: 'var(--amber-600)'  },
  { key: 'confluence', label: 'Confluence delivery', sub: 'Post-mortem page',               dot: 'var(--purple-600)' },
]

export default function App() {
  const [form, setForm] = useState(SAMPLE)
  const [activeNav, setActiveNav] = useState(0)
  const [stageStatus, setStageStatus] = useState({ extraction: 'pending', timeline: 'pending', quality: 'pending', confluence: 'pending' })
  const [results, setResults] = useState({})
  const [running, setRunning] = useState(false)
  const [error, setError] = useState(null)
  const [openStages, setOpenStages] = useState({})

  function set(field) { return (val) => setForm(f => ({ ...f, [field]: val })) }

  function toggleStage(key) {
    setOpenStages(s => ({ ...s, [key]: !s[key] }))
  }

  async function runPipeline() {
    setRunning(true)
    setError(null)
    setResults({})
    setStageStatus({ extraction: 'running', timeline: 'pending', quality: 'pending', confluence: 'pending' })
    setOpenStages({ extraction: true, timeline: true, quality: true, confluence: true })

    try {
      // Show all stages as running after a brief stagger
      setTimeout(() => setStageStatus(s => ({ ...s, timeline: 'running', quality: 'running' })), 600)
      setTimeout(() => setStageStatus(s => ({ ...s, confluence: 'running' })), 1200)

      const res = await runFullRCA({
        incident_id:      form.incident_id,
        severity:         form.severity,
        ci:               form.ci,
        opened_at:        form.opened_at,
        closed_at:        form.closed_at,
        team:             form.team,
        work_notes:       form.work_notes,
        resolution_notes: form.resolution_notes,
      })

      setResults(res)
      setStageStatus({
        extraction: res.extraction ? 'done'  : 'error',
        timeline:   res.timeline   ? 'done'  : (res.errors?.timeline   ? 'error' : 'done'),
        quality:    res.quality    ? (res.quality.overall_quality === 'low' ? 'warn' : 'done') : 'error',
        confluence: res.confluence ? 'done'  : (res.errors?.confluence ? 'error' : 'done'),
      })
    } catch (e) {
      setError(e.message)
      setStageStatus({ extraction: 'error', timeline: 'error', quality: 'error', confluence: 'error' })
    } finally {
      setRunning(false)
    }
  }

  function resetAll() {
    setResults({})
    setError(null)
    setStageStatus({ extraction: 'pending', timeline: 'pending', quality: 'pending', confluence: 'pending' })
    setOpenStages({})
  }

  return (
    <div style={{ display: 'grid', gridTemplateColumns: '240px 1fr', minHeight: '100vh' }}>

      {/* ── Sidebar ────────────────────────────────────────────── */}
      <aside style={{ background: 'white', borderRight: '1px solid var(--gray-100)', display: 'flex', flexDirection: 'column' }}>
        <div style={{ padding: '20px 20px 16px', borderBottom: '1px solid var(--gray-100)' }}>
          <div style={{ fontSize: 15, fontWeight: 600, color: 'var(--gray-800)' }}>RCA Agent</div>
          <div style={{ fontSize: 12, color: 'var(--gray-600)', marginTop: 2 }}>Incident Analysis Pipeline</div>
        </div>

        <div style={{ padding: '8px 0' }}>
          <div style={{ padding: '6px 20px 4px', fontSize: 11, fontWeight: 600, color: 'var(--gray-600)', textTransform: 'uppercase', letterSpacing: '0.5px' }}>
            Pipeline stages
          </div>
          {STAGES.map((s, i) => {
            const active = activeNav === i
            return (
              <div
                key={s.key}
                onClick={() => { setActiveNav(i); if (!openStages[s.key]) toggleStage(s.key) }}
                style={{
                  display: 'flex', alignItems: 'center', gap: 10,
                  padding: '8px 20px', cursor: 'pointer',
                  borderLeft: `3px solid ${active ? s.dot : 'transparent'}`,
                  background: active ? 'var(--blue-50)' : 'transparent',
                  transition: 'background 0.12s',
                }}
              >
                <span style={{ width: 8, height: 8, borderRadius: '50%', background: s.dot, flexShrink: 0 }} />
                <div>
                  <div style={{ fontSize: 13, fontWeight: active ? 500 : 400, color: active ? 'var(--blue-800)' : 'var(--gray-700)' }}>{s.label}</div>
                  <StatusPill status={stageStatus[s.key]} />
                </div>
              </div>
            )
          })}
        </div>

        <div style={{ marginTop: 'auto', padding: '16px 20px', borderTop: '1px solid var(--gray-100)', fontSize: 12, color: 'var(--gray-600)' }}>
          Powered by Vertex AI / Gemini
        </div>
      </aside>

      {/* ── Main ───────────────────────────────────────────────── */}
      <main style={{ padding: 28, overflowY: 'auto' }}>
        <div style={{ marginBottom: 24 }}>
          <h1 style={{ fontSize: 22, fontWeight: 500 }}>Incident RCA Generator</h1>
          <p style={{ fontSize: 14, color: 'var(--gray-600)', marginTop: 4 }}>
            Fill in incident details and run the full AI-powered analysis pipeline.
            The backend is also available as a standalone REST API — see{' '}
            <a href={`${import.meta.env.VITE_API_URL || ''}/docs`} target="_blank" rel="noreferrer">/docs</a>.
          </p>
        </div>

        {/* Incident form */}
        <Card>
          <SectionTitle>Incident details</SectionTitle>
          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 12 }}>
            <FormField label="Incident ID">
              <Input value={form.incident_id} onChange={set('incident_id')} placeholder="INC0012345" />
            </FormField>
            <FormField label="Severity">
              <Select value={form.severity} onChange={set('severity')}>
                <option>SEV1 - Critical</option>
                <option>SEV2 - Major</option>
                <option>SEV3 - Minor</option>
              </Select>
            </FormField>
            <FormField label="Affected service / CI">
              <Input value={form.ci} onChange={set('ci')} placeholder="payments-api (CMDB: CI-00291)" />
            </FormField>
            <FormField label="Team">
              <Input value={form.team} onChange={set('team')} placeholder="Platform Reliability Engineering" />
            </FormField>
            <FormField label="Incident opened">
              <Input value={form.opened_at} onChange={set('opened_at')} placeholder="2025-06-14 02:17 UTC" />
            </FormField>
            <FormField label="Incident resolved">
              <Input value={form.closed_at} onChange={set('closed_at')} placeholder="2025-06-14 05:44 UTC" />
            </FormField>
            <FormField label="Work notes (raw ServiceNow export)" full>
              <Textarea value={form.work_notes} onChange={set('work_notes')} rows={7}
                placeholder="Paste audit log / work notes here..." />
            </FormField>
            <FormField label="Resolution notes (from assignee)" full>
              <Textarea value={form.resolution_notes} onChange={set('resolution_notes')} rows={4}
                placeholder="What was the root cause and how was it fixed?" />
            </FormField>
          </div>
          <div style={{ display: 'flex', gap: 10, marginTop: 18 }}>
            <Btn onClick={runPipeline} disabled={running}>
              {running ? <span style={{ display: 'flex', alignItems: 'center', gap: 8 }}><Spinner />Running pipeline…</span> : 'Run full RCA pipeline'}
            </Btn>
            <Btn variant="secondary" onClick={resetAll} disabled={running}>Reset</Btn>
          </div>
        </Card>

        {error && (
          <div style={{ background: 'var(--red-50)', border: '1px solid var(--red-200)', borderRadius: 'var(--radius-md)', padding: '12px 16px', marginBottom: 16, fontSize: 13, color: 'var(--red-600)' }}>
            Pipeline error: {error}
          </div>
        )}

        {/* Pipeline stage cards */}
        {STAGES.map((s, i) => {
          const status = stageStatus[s.key]
          const open = openStages[s.key]
          const panelData = results[s.key === 'extraction' ? 'extraction'
            : s.key === 'timeline'   ? 'timeline'
            : s.key === 'quality'    ? 'quality'
            : 'confluence']

          const numColor = {
            pending: { bg: 'var(--gray-50)',   c: 'var(--gray-600)'  },
            running: { bg: 'var(--blue-50)',   c: 'var(--blue-800)'  },
            done:    { bg: 'var(--teal-50)',   c: 'var(--teal-800)'  },
            warn:    { bg: 'var(--amber-50)',  c: 'var(--amber-800)' },
            error:   { bg: 'var(--red-50)',    c: 'var(--red-600)'   },
          }[status] || { bg: 'var(--gray-50)', c: 'var(--gray-600)' }

          return (
            <div key={s.key} style={{ background: 'white', border: '1px solid var(--gray-100)', borderRadius: 'var(--radius-lg)', marginBottom: 12, overflow: 'hidden' }}>
              {/* Stage header */}
              <div
                onClick={() => toggleStage(s.key)}
                style={{ display: 'flex', alignItems: 'center', gap: 12, padding: '13px 20px', cursor: 'pointer' }}
                onMouseEnter={e => e.currentTarget.style.background = 'var(--gray-50)'}
                onMouseLeave={e => e.currentTarget.style.background = 'white'}
              >
                <div style={{
                  width: 28, height: 28, borderRadius: '50%', flexShrink: 0,
                  display: 'flex', alignItems: 'center', justifyContent: 'center',
                  background: numColor.bg, color: numColor.c, fontSize: 12, fontWeight: 600,
                }}>
                  {status === 'running' ? <Spinner size={12} /> : i + 1}
                </div>
                <div style={{ flex: 1 }}>
                  <div style={{ fontSize: 14, fontWeight: 500 }}>{s.label}</div>
                  <div style={{ fontSize: 12, color: 'var(--gray-600)', marginTop: 1 }}>{s.sub}</div>
                </div>
                <StatusPill status={status} />
                <span style={{ fontSize: 12, color: 'var(--gray-600)', marginLeft: 4 }}>{open ? '▲' : '▼'}</span>
              </div>

              {/* Stage body */}
              {open && (
                <div style={{ padding: '0 20px 18px', borderTop: '1px solid var(--gray-100)', paddingTop: 14 }}>
                  {status === 'running'
                    ? <div style={{ display: 'flex', alignItems: 'center', gap: 8, color: 'var(--gray-600)', fontSize: 13, padding: '12px 0' }}><Spinner />Analysing with Gemini…</div>
                    : s.key === 'extraction' ? <ExtractionPanel data={results.extraction} />
                    : s.key === 'timeline'   ? <TimelinePanel   data={results.timeline}   />
                    : s.key === 'quality'    ? <QualityPanel    data={results.quality}    />
                    : <ConfluencePanel data={results.confluence} incidentId={form.incident_id} />
                  }
                </div>
              )}
            </div>
          )
        })}
      </main>
    </div>
  )
}
