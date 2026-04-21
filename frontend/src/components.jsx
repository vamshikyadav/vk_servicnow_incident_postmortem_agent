import React from 'react'

/* ── Card ─────────────────────────────────────────────────────── */
export function Card({ children, style }) {
  return (
    <div style={{
      background: 'white',
      border: '1px solid var(--gray-100)',
      borderRadius: 'var(--radius-lg)',
      padding: '20px 24px',
      marginBottom: 16,
      ...style,
    }}>
      {children}
    </div>
  )
}

/* ── SectionTitle ─────────────────────────────────────────────── */
export function SectionTitle({ children }) {
  return (
    <div style={{
      fontSize: 11,
      fontWeight: 600,
      color: 'var(--gray-600)',
      textTransform: 'uppercase',
      letterSpacing: '0.5px',
      marginBottom: 14,
    }}>
      {children}
    </div>
  )
}

/* ── Badge ────────────────────────────────────────────────────── */
export function Badge({ children, color = 'blue' }) {
  const map = {
    blue:   { bg: 'var(--blue-50)',   color: 'var(--blue-800)'   },
    teal:   { bg: 'var(--teal-50)',   color: 'var(--teal-800)'   },
    amber:  { bg: 'var(--amber-50)',  color: 'var(--amber-800)'  },
    red:    { bg: 'var(--red-50)',    color: 'var(--red-600)'    },
    green:  { bg: 'var(--green-50)',  color: 'var(--green-600)'  },
    purple: { bg: 'var(--purple-50)', color: 'var(--purple-800)' },
    gray:   { bg: 'var(--gray-100)',  color: 'var(--gray-700)'   },
  }
  const s = map[color] || map.gray
  return (
    <span style={{
      display: 'inline-block',
      padding: '2px 9px',
      borderRadius: 20,
      fontSize: 11,
      fontWeight: 600,
      background: s.bg,
      color: s.color,
    }}>
      {children}
    </span>
  )
}

/* ── Btn ──────────────────────────────────────────────────────── */
export function Btn({ children, onClick, variant = 'primary', disabled, style }) {
  const map = {
    primary:   { background: 'var(--blue-600)',  color: '#fff' },
    secondary: { background: 'var(--gray-100)',  color: 'var(--gray-800)' },
    success:   { background: 'var(--green-600)', color: '#fff' },
    danger:    { background: 'var(--red-600)',   color: '#fff' },
  }
  const s = map[variant] || map.primary
  return (
    <button
      onClick={onClick}
      disabled={disabled}
      style={{
        padding: '9px 20px',
        borderRadius: 'var(--radius-md)',
        fontSize: 13,
        fontWeight: 500,
        ...s,
        opacity: disabled ? 0.45 : 1,
        cursor: disabled ? 'not-allowed' : 'pointer',
        transition: 'opacity 0.15s',
        ...style,
      }}
    >
      {children}
    </button>
  )
}

/* ── FormField ────────────────────────────────────────────────── */
export function FormField({ label, children, full }) {
  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 5, gridColumn: full ? '1 / -1' : undefined }}>
      <label style={{ fontSize: 12, fontWeight: 500, color: 'var(--gray-600)' }}>{label}</label>
      {children}
    </div>
  )
}

const inputStyle = {
  border: '1px solid var(--gray-100)',
  borderRadius: 'var(--radius-md)',
  padding: '8px 12px',
  fontSize: 13,
  color: 'var(--gray-800)',
  background: 'white',
  outline: 'none',
  width: '100%',
  transition: 'border-color 0.15s',
}

export function Input({ value, onChange, placeholder, onFocus, onBlur, style }) {
  return (
    <input
      value={value}
      onChange={e => onChange(e.target.value)}
      placeholder={placeholder}
      style={{ ...inputStyle, ...style }}
      onFocus={e => e.target.style.borderColor = 'var(--blue-200)'}
      onBlur={e => e.target.style.borderColor = 'var(--gray-100)'}
    />
  )
}

export function Textarea({ value, onChange, placeholder, rows = 5 }) {
  return (
    <textarea
      value={value}
      onChange={e => onChange(e.target.value)}
      placeholder={placeholder}
      rows={rows}
      style={{ ...inputStyle, resize: 'vertical', lineHeight: 1.6 }}
      onFocus={e => e.target.style.borderColor = 'var(--blue-200)'}
      onBlur={e => e.target.style.borderColor = 'var(--gray-100)'}
    />
  )
}

export function Select({ value, onChange, children }) {
  return (
    <select
      value={value}
      onChange={e => onChange(e.target.value)}
      style={{ ...inputStyle, cursor: 'pointer' }}
    >
      {children}
    </select>
  )
}

/* ── Spinner ──────────────────────────────────────────────────── */
export function Spinner({ size = 14 }) {
  return (
    <span style={{
      display: 'inline-block',
      width: size,
      height: size,
      border: `2px solid var(--gray-100)`,
      borderTopColor: 'var(--blue-600)',
      borderRadius: '50%',
      animation: 'spin 0.7s linear infinite',
    }} />
  )
}

/* ── StatusPill ───────────────────────────────────────────────── */
export function StatusPill({ status }) {
  const map = {
    pending:  { label: 'Pending',  color: 'gray'  },
    running:  { label: 'Running',  color: 'blue'  },
    done:     { label: 'Complete', color: 'teal'  },
    warn:     { label: 'Warning',  color: 'amber' },
    error:    { label: 'Error',    color: 'red'   },
  }
  const s = map[status] || map.pending
  return <Badge color={s.color}>{s.label}</Badge>
}

/* ── DataTable ────────────────────────────────────────────────── */
export function DataTable({ rows }) {
  return (
    <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: 12 }}>
      <tbody>
        {rows.map(([k, v], i) => (
          <tr key={i} style={{ borderBottom: '1px solid var(--gray-100)' }}>
            <td style={{ padding: '6px 10px', color: 'var(--gray-600)', fontWeight: 500, whiteSpace: 'nowrap', width: 160 }}>{k}</td>
            <td style={{ padding: '6px 10px', color: 'var(--gray-800)' }}>{v}</td>
          </tr>
        ))}
      </tbody>
    </table>
  )
}

/* ── MetricBox ────────────────────────────────────────────────── */
export function MetricBox({ value, unit, label }) {
  return (
    <div style={{ background: 'var(--gray-50)', borderRadius: 'var(--radius-md)', padding: '14px 16px' }}>
      <div style={{ fontSize: 24, fontWeight: 500, color: 'var(--gray-800)' }}>
        {value}<span style={{ fontSize: 13 }}>{unit}</span>
      </div>
      <div style={{ fontSize: 11, color: 'var(--gray-600)', marginTop: 2 }}>{label}</div>
    </div>
  )
}

/* ── EmptyState ───────────────────────────────────────────────── */
export function EmptyState({ text = 'Run the pipeline to see results' }) {
  return (
    <div style={{ textAlign: 'center', padding: '28px 16px', color: 'var(--gray-600)', fontSize: 13 }}>
      {text}
    </div>
  )
}

/* Inject keyframes once */
if (typeof document !== 'undefined' && !document.getElementById('rca-keyframes')) {
  const s = document.createElement('style')
  s.id = 'rca-keyframes'
  s.textContent = '@keyframes spin { to { transform: rotate(360deg); } }'
  document.head.appendChild(s)
}
