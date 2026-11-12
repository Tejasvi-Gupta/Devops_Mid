import React from 'react'
import { Link } from 'react-router-dom'
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
}

export function StatusPill({ value }) {
  const tone = {
    ready: 'bg-emerald-100 text-emerald-900 dark:bg-emerald-950 dark:text-emerald-200',
    completed: 'bg-emerald-100 text-emerald-900 dark:bg-emerald-950 dark:text-emerald-200',
    failed: 'bg-red-100 text-red-900 dark:bg-red-950 dark:text-red-200',
    needs_attention: 'bg-amber-100 text-amber-950 dark:bg-amber-950 dark:text-amber-100',
    needs_update: 'bg-amber-100 text-amber-950 dark:bg-amber-950 dark:text-amber-100',
    installing: 'bg-sky-100 text-sky-950 dark:bg-sky-950 dark:text-sky-100',
  }[value] || 'bg-stone-200 text-stone-800 dark:bg-stone-800 dark:text-stone-100'
  return <span className={`rounded-full px-2.5 py-1 text-xs font-medium ${tone}`}>{LABELS[value] || value}</span>
}

export function Shell({ children }) {
  const { user, logout } = useAuth()
  const links = user?.role === 'admin'
    ? [['/admin', 'Admin'], ['/notifications', 'Notifications'], ['/account', 'Account']]
    : user?.role === 'instructor' && user.instructor_status === 'approved'
      ? [['/instructor', 'Courses'], ['/notifications', 'Notifications'], ['/account', 'Account']]
      : [['/student', 'Environments'], ['/student/device', 'Device'], ['/notifications', 'Notifications'], ['/account', 'Account']]
  return (
    <div className="min-h-screen bg-paper text-ink dark:bg-zinc-950 dark:text-stone-100">
      <header className="border-b border-stone-300 dark:border-zinc-800">
        <div className="mx-auto flex max-w-6xl items-center justify-between gap-4 px-4 py-4">
          <Link to={user ? links[0][0] : '/login'} className="font-medium tracking-tight">Provision</Link>
          <nav className="flex flex-wrap items-center gap-4 text-sm">
            {user && links.map(([href, label]) => <Link key={href} to={href}>{label}</Link>)}
            <button type="button" className="rounded border border-stone-400 px-2 py-1 dark:border-zinc-600" onClick={() => {
              const next = document.documentElement.classList.toggle('dark')
              localStorage.setItem('epp-theme', next ? 'dark' : 'light')
            }}>Theme</button>
            {user && <button type="button" onClick={logout}>Sign out</button>}
          </nav>
        </div>
      </header>
      <main className="mx-auto max-w-6xl px-4 py-8">{children}</main>
    </div>
  )
}

export function Panel({ title, children, action }) {
  return (
    <section className="rounded-lg border border-stone-300 bg-white p-5 dark:border-zinc-800 dark:bg-zinc-900">
      <div className="mb-4 flex items-center justify-between gap-3">
        <h2 className="text-lg font-medium">{title}</h2>
        {action}
      </div>
      {children}
    </section>
  )
}

export function Field({ label, children }) {
  return <label className="block text-sm"><span className="mb-1 block text-stone-600 dark:text-stone-300">{label}</span>{children}</label>
}

export const inputClass = 'w-full rounded border border-stone-300 bg-white px-3 py-2 dark:border-zinc-700 dark:bg-zinc-950'

export function PlanPreview({ plan }) {
  if (!plan) return <p>The agent has not reported a plan yet.</p>
  return (
    <div className="space-y-3">
      {plan.uncertainties?.length > 0 && <p className="text-sm text-clay">{plan.uncertainties.join(' ')}</p>}
      <ul className="space-y-3">
        {(plan.actions || []).map((action) => (
          <li key={action.id} className="rounded border border-stone-200 p-3 dark:border-zinc-700">
            <div className="flex items-center justify-between gap-3">
              <strong className="font-mono text-sm">{action.tool}</strong>
              <StatusPill value={action.operation} />
            </div>
            <p className="mt-2 text-sm">{action.reason}</p>
            <p className="mt-1 text-sm text-stone-600 dark:text-stone-300">{action.impact}</p>
            {action.version && <p className="mt-1 font-mono text-xs">Target {action.version}</p>}
          </li>
        ))}
      </ul>
    </div>
  )
}
