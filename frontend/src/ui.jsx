import React from 'react'
import { Link, useLocation } from 'react-router-dom'
import { useAuth } from './auth'

const LABELS = {
  ready: 'Ready',
  not_ready: 'Not ready',
  not_checked: 'Not checked',
  needs_update: 'Needs update',
  in_progress: 'In progress',
  pending: 'Pending',
  planning: 'Planning',
  awaiting_approval: 'Awaiting approval',
  installing: 'Installing',
  verifying: 'Verifying',
  completed: 'Completed',
  failed: 'Failed',
  cancelled: 'Cancelled',
  needs_attention: 'Needs attention',
  approved: 'Approved',
  active: 'Active',
  suspended: 'Suspended',
  revoked: 'Revoked',
  draft: 'Draft',
  published: 'Published',
}

const STATUS_TONES = {
  ready: 'success',
  completed: 'success',
  published: 'success',
  failed: 'danger',
  cancelled: 'danger',
  revoked: 'danger',
  needs_attention: 'warning',
  needs_update: 'warning',
  installing: 'info',
  verifying: 'info',
  in_progress: 'info',
  awaiting_approval: 'warning',
}

export function StatusPill({ value }) {
  const tone = STATUS_TONES[value] || 'neutral'
  return <span className={`status-pill status-${tone}`}><span aria-hidden="true" className="status-dot" />{LABELS[value] || value}</span>
}

export function Alert({ tone = 'danger', children }) {
  return <div className={`alert alert-${tone}`} role={tone === 'danger' ? 'alert' : 'status'}>{children}</div>
}

export function LoadingState({ label = 'Loading' }) {
  return <div className="loading-state" role="status"><span className="spinner" aria-hidden="true" />{label}…</div>
}

export function EmptyState({ title, children, action }) {
  return <div className="empty-state"><div className="empty-icon" aria-hidden="true">⌁</div><h3>{title}</h3>{children && <p>{children}</p>}{action}</div>
}

export function Shell({ children }) {
  const { user, logout } = useAuth()
  const location = useLocation()
  const links = user?.role === 'instructor'
    ? [['/instructor', 'Courses', '▦'], ['/notifications', 'Notifications', '◌'], ['/account', 'Account', '○']]
    : [['/student', 'Environments', '▦'], ['/student/device', 'Device', '⌁'], ['/notifications', 'Notifications', '◌'], ['/account', 'Account', '○']]

  return (
    <div className="app-shell">
      {user && <aside className="sidebar">
        <Link to={links[0][0]} className="brand"><span className="brand-mark">L</span><span>Lab<span>Grid</span></span></Link>
        <div className="sidebar-label">{user.role === 'instructor' ? 'Instructor workspace' : 'Student workspace'}</div>
        <nav className="side-nav" aria-label="Primary navigation">
          {links.map(([href, label, icon]) => <Link className={location.pathname === href || (href !== links[0][0] && location.pathname.startsWith(href)) ? 'nav-link active' : 'nav-link'} key={href} to={href}><span aria-hidden="true">{icon}</span>{label}</Link>)}
        </nav>
        <div className="sidebar-footer">
          <div className="profile-mini"><span className="avatar">{user.name?.slice(0, 1).toUpperCase()}</span><span><strong>{user.name}</strong><small>{user.role}</small></span></div>
          <button type="button" className="sign-out" onClick={logout}>Sign out</button>
        </div>
      </aside>}
      <div className={user ? 'app-content has-sidebar' : 'app-content'}>
        {!user && <header className="public-header"><Link to="/login" className="brand"><span className="brand-mark">L</span><span>Lab<span>Grid</span></span></Link></header>}
        {user && <header className="mobile-header"><Link to={links[0][0]} className="brand"><span className="brand-mark">L</span><span>Lab<span>Grid</span></span></Link><nav className="mobile-nav" aria-label="Mobile navigation">{links.slice(0, 3).map(([href, label]) => <Link key={href} className={location.pathname.startsWith(href) ? 'active' : ''} to={href}>{label}</Link>)}</nav><button type="button" className="mobile-sign-out" onClick={logout}>Sign out</button></header>}
        <main className="page-container">{children}</main>
      </div>
    </div>
  )
}

export function PageHeader({ eyebrow, title, description, action }) {
  return <div className="page-header"><div>{eyebrow && <div className="eyebrow">{eyebrow}</div>}<h1>{title}</h1>{description && <p>{description}</p>}</div>{action && <div className="page-header-action">{action}</div>}</div>
}

export function Panel({ title, children, action, className = '' }) {
  return <section className={`panel ${className}`}><div className="panel-heading"><h2>{title}</h2>{action}</div>{children}</section>
}

export function Field({ label, children, hint }) {
  return <label className="field"><span className="field-label">{label}</span>{children}{hint && <span className="field-hint">{hint}</span>}</label>
}

export const inputClass = 'form-control'

export function PlanPreview({ plan }) {
  if (!plan) return <EmptyState title="Plan is being prepared">The agent has not reported an installation plan yet.</EmptyState>
  return (
    <div className="plan-preview">
      {plan.uncertainties?.length > 0 && <Alert tone="warning">{plan.uncertainties.join(' ')}</Alert>}
      <div className="plan-list">
        {(plan.actions || []).map((action) => (
          <article key={action.id} className="plan-item">
            <div className="plan-item-top"><strong>{action.tool}</strong><StatusPill value={action.operation} /></div>
            <p>{action.reason}</p>
            <span>{action.impact}</span>
            {action.version && <code>Target {action.version}</code>}
          </article>
        ))}
      </div>
    </div>
  )
}
