import { useEffect, useState } from 'react'
import { Link, useNavigate, useParams } from 'react-router-dom'
import { api } from './api'
import { homeFor, useAuth } from './auth'
import { Field, Panel, PlanPreview, StatusPill, inputClass } from './ui'

function useLoad(loader, deps = []) {
  const [data, setData] = useState(null)
  const [error, setError] = useState('')
  const [tick, setTick] = useState(0)
  useEffect(() => {
    let active = true
    loader().then((value) => active && setData(value)).catch((err) => active && setError(err.message))
    return () => { active = false }
  }, [...deps, tick])
  return { data, error, reload: () => setTick((value) => value + 1) }
}

export function LoginPage() {
  const { login } = useAuth()
  const navigate = useNavigate()
  const [error, setError] = useState('')
  return (
    <Panel title="Sign in">
      <form className="space-y-4" onSubmit={async (event) => {
        event.preventDefault()
        const form = new FormData(event.target)
        try {
          const user = await login(form.get('email'), form.get('password'))
          navigate(homeFor(user))
        } catch (err) { setError(err.message) }
      }}>
        <Field label="Email"><input className={inputClass} name="email" type="email" required /></Field>
        <Field label="Password"><input className={inputClass} name="password" type="password" required /></Field>
        {error && <p className="text-sm text-red-700">{error}</p>}
        <button className="rounded bg-pine px-4 py-2 text-white" type="submit">Sign in</button>
      </form>
      <p className="mt-4 text-sm">No account? <Link to="/register">Register</Link></p>
      <p className="mt-2 text-sm text-stone-600">Google sign-in appears after GOOGLE_CLIENT_ID is configured.</p>
    </Panel>
  )
}

export function RegisterPage() {
  const { register } = useAuth()
  const navigate = useNavigate()
  const [error, setError] = useState('')
  return (
    <Panel title="Create an account">
      <form className="space-y-4" onSubmit={async (event) => {
        event.preventDefault()
        const form = new FormData(event.target)
        try {
          const user = await register({
            name: form.get('name'),
            email: form.get('email'),
            password: form.get('password'),
            requested_role: form.get('role'),
          })
          navigate(homeFor(user))
        } catch (err) { setError(err.message) }
      }}>
        <Field label="Name"><input className={inputClass} name="name" required /></Field>
        <Field label="Email"><input className={inputClass} name="email" type="email" required /></Field>
        <Field label="Password">
          <input className={inputClass} name="password" type="password" minLength={12} required />
          <span className="mt-1 block text-xs text-stone-500">At least 12 characters, with a letter and a number. Example: correct-horse-1</span>
        </Field>
        <Field label="Role">
          <select className={inputClass} name="role"><option value="student">Student</option><option value="instructor">Instructor</option></select>
        </Field>
        {error && <p className="text-sm text-red-700">{error}</p>}
        <button className="rounded bg-pine px-4 py-2 text-white" type="submit">Register</button>
      </form>
    </Panel>
  )
}

export function AccountPage() {
  const { user } = useAuth()
  return (
    <Panel title="Account">
      <p>{user?.name}</p>
      <p className="text-sm text-stone-600">{user?.email}</p>
      <p className="mt-3">Role: {user?.role}</p>
      {user?.role === 'instructor' && user.instructor_status === 'pending' && <p className="mt-3">An administrator still needs to approve instructor access.</p>}
      {user?.instructor_status === 'rejected' && <p className="mt-3">Instructor access was rejected. You can keep using a student account.</p>}
    </Panel>
  )
}

export function AccessDenied() {
  return <Panel title="Access denied"><p>This account cannot open that page.</p></Panel>
}

export function NotificationsPage() {
  const { data, error } = useLoad(() => api('/notifications'))
  if (error) return <p>{error}</p>
  if (!data) return <p>Loading notifications…</p>
  if (!data.items.length) return <Panel title="Notifications"><p>No notifications yet.</p></Panel>
  return (
    <Panel title="Notifications">
      <ul className="space-y-3">
        {data.items.map((item) => (
          <li key={item.id} className="border-b border-stone-200 pb-3 dark:border-zinc-800">
            <div className="flex items-center justify-between"><strong>{item.type.replaceAll('_', ' ')}</strong><span className="text-xs">{new Date(item.created_at).toLocaleString()}</span></div>
            <p className="text-sm text-stone-600">{item.payload.summary || item.payload.course_name || item.payload.display_name || ''}</p>
          </li>
        ))}
      </ul>
    </Panel>
  )
}

export function StudentHome() {
  const { data, error } = useLoad(() => api('/student/environments'))
  if (error) return <p>{error}</p>
  if (!data) return <p>Loading environments…</p>
  return (
    <Panel title="Assigned environments">
      {!data.length && <p>No course environment is assigned yet.</p>}
      <ul className="space-y-3">
        {data.map((item) => (
          <li key={item.environment_id} className="flex items-center justify-between gap-3">
            <div>
              <Link className="font-medium" to={`/student/environments/${item.environment_id}`}>{item.course_name} · {item.name}</Link>
              <p className="text-sm text-stone-600">{item.class_code}</p>
            </div>
            <StatusPill value={item.status} />
          </li>
        ))}
      </ul>
    </Panel>
  )
}

export function DevicePage() {
  const { data, error, reload } = useLoad(() => api('/devices'))
  const [code, setCode] = useState('')
  const [message, setMessage] = useState('')
  async function createCode(replace) {
    setMessage('')
    try {
      const result = await api('/devices/pairing-codes', { method: 'POST', body: JSON.stringify({ replace_existing: replace }) })
      setCode(result.pairing_code)
    } catch (err) { setMessage(err.message) }
  }
  return (
    <Panel title="Windows device">
      {error && <p>{error}</p>}
      {!data && <p>Loading device…</p>}
      {data && !data.length && <p>No device is paired.</p>}
      <ul className="space-y-2">
        {data?.map((device) => (
          <li key={device.id} className="flex items-center justify-between">
            <span>{device.display_name} · last seen {device.last_seen_at ? new Date(device.last_seen_at).toLocaleString() : 'never'}</span>
            <span className="flex items-center gap-2"><StatusPill value={device.status} />{device.status === 'active' && <button type="button" onClick={async () => { await api(`/devices/${device.id}/revoke`, { method: 'POST' }); reload() }}>Revoke</button>}</span>
          </li>
        ))}
      </ul>
      <div className="mt-4 flex gap-2">
        <button className="rounded bg-pine px-3 py-2 text-white" type="button" onClick={() => createCode(false)}>Create pairing code</button>
        <button className="rounded border px-3 py-2" type="button" onClick={() => createCode(true)}>Replace device</button>
      </div>
      {code && <p className="mt-4 font-mono text-2xl">{code}</p>}
      {code && <p className="mt-2 text-sm">Enter this code in the agent within five minutes. It works once.</p>}
      {message && <p className="mt-3 text-sm text-red-700">{message}</p>}
    </Panel>
  )
}

export function StudentEnvironment() {
  const { id } = useParams()
  const navigate = useNavigate()
  const { data, error } = useLoad(() => api(`/environments/${id}`), [id])
  const [message, setMessage] = useState('')
  async function start(operation) {
    setMessage('')
    try {
      const job = await api('/jobs', { method: 'POST', body: JSON.stringify({ environment_id: id, idempotency_key: crypto.randomUUID(), operation }) })
      navigate(`/student/jobs/${job.id}`)
    } catch (err) { setMessage(err.message) }
  }
  if (error) return <p>{error}</p>
  if (!data) return <p>Loading environment…</p>
  const published = data.revisions.find((item) => item.id === data.current_published_revision_id)
  const requirements = published?.specification.requirements || []
  return (
    <div className="space-y-6">
      <Panel title={data.name} action={<StatusPill value={published ? 'active' : 'pending'} />}>
        <p className="text-sm text-stone-600">{data.description || 'No description'}</p>
        {!published && <p className="mt-3">The instructor has not published a revision yet.</p>}
        <table className="mt-4 w-full text-left text-sm">
          <thead><tr><th>Tool</th><th>Constraint</th><th>Required</th></tr></thead>
          <tbody>
            {requirements.map((item) => <tr key={item.tool} className="border-t border-stone-200 dark:border-zinc-800"><td className="py-2 font-mono">{item.display_name}</td><td className="font-mono">{item.version_constraint}</td><td>{item.mandatory ? 'Mandatory' : 'Optional'}</td></tr>)}
          </tbody>
        </table>
        <div className="mt-4 flex gap-2">
          <button className="rounded bg-pine px-3 py-2 text-white" type="button" onClick={() => start('provision')}>Set up environment</button>
          <button className="rounded border px-3 py-2" type="button" onClick={() => start('verify')}>Verify</button>
        </div>
        {message && <p className="mt-3 text-sm text-red-700">{message}</p>}
      </Panel>
    </div>
  )
}

export function JobPage() {
  const { id } = useParams()
  const [job, setJob] = useState(null)
  const [error, setError] = useState('')
  const [acks, setAcks] = useState([])
  useEffect(() => {
    let stop = false
    const load = () => api(`/jobs/${id}`).then((value) => !stop && setJob(value)).catch((err) => !stop && setError(err.message))
    load()
    const timer = setInterval(load, 2000)
    return () => { stop = true; clearInterval(timer) }
  }, [id])
  if (error) return <p>{error}</p>
  if (!job) return <p>Loading job…</p>
  const required = job.plan?.required_acknowledgements || []
  const terminal = ['completed', 'failed', 'cancelled', 'needs_attention'].includes(job.status)
  return (
    <div className="space-y-6">
      <Panel title="Setup job" action={<StatusPill value={job.status} />}>
        {job.error_summary && <p className="mb-3 text-sm">{job.error_summary}</p>}
        <PlanPreview plan={job.plan} />
        {job.status === 'awaiting_approval' && (
          <form className="mt-4 space-y-2" onSubmit={async (event) => {
            event.preventDefault()
            const updated = await api(`/jobs/${id}/approve`, { method: 'POST', body: JSON.stringify({ acknowledgements: acks }) })
            setJob(updated)
          }}>
            {required.map((item) => (
              <label key={item} className="block text-sm">
                <input className="mr-2" type="checkbox" checked={acks.includes(item)} onChange={(event) => setAcks(event.target.checked ? [...acks, item] : acks.filter((value) => value !== item))} />
                I understand: {item.replaceAll('_', ' ')}
              </label>
            ))}
            <button className="rounded bg-pine px-3 py-2 text-white" type="submit">Approve plan</button>
          </form>
        )}
        <div className="mt-4 flex gap-2">
          {!terminal && <button type="button" onClick={async () => setJob(await api(`/jobs/${id}/cancel`, { method: 'POST' }))}>Cancel</button>}
          {['failed', 'cancelled', 'needs_attention'].includes(job.status) && <button type="button" onClick={async () => {
            const created = await api(`/jobs/${id}/retry?idempotency_key=${crypto.randomUUID()}`, { method: 'POST' })
            window.location.assign(`/student/jobs/${created.id}`)
          }}>Retry</button>}
        </div>
      </Panel>
    </div>
  )
}

export function InstructorHome() {
  const { data, error, reload } = useLoad(() => api('/courses'))
  const [message, setMessage] = useState('')
  return (
    <div className="space-y-6">
      <Panel title="Create a course">
        <form className="grid gap-3 md:grid-cols-3" onSubmit={async (event) => {
          event.preventDefault()
          const form = new FormData(event.target)
          try {
            await api('/courses', { method: 'POST', body: JSON.stringify({ name: form.get('name'), class_code: form.get('class_code'), description: form.get('description') }) })
            event.target.reset()
            reload()
          } catch (err) { setMessage(err.message) }
        }}>
          <input className={inputClass} name="name" placeholder="Course name" required />
          <input className={inputClass} name="class_code" placeholder="Class code" />
          <input className={inputClass} name="description" placeholder="Description" />
          <button className="rounded bg-pine px-3 py-2 text-white md:col-span-3" type="submit">Create course</button>
        </form>
        {message && <p className="mt-2 text-sm text-red-700">{message}</p>}
      </Panel>
      <Panel title="Courses">
        {error && <p>{error}</p>}
        {!data && <p>Loading courses…</p>}
        {data && !data.length && <p>No courses yet.</p>}
        <ul>{data?.map((course) => <li key={course.id} className="py-2"><Link to={`/instructor/courses/${course.id}`}>{course.name} · {course.class_code}</Link></li>)}</ul>
      </Panel>
    </div>
  )
}

export function InstructorCourse() {
  const { id } = useParams()
  const [course, setCourse] = useState(null)
  const [environments, setEnvironments] = useState([])
  const [roster, setRoster] = useState([])
  const [readiness, setReadiness] = useState([])
  const [message, setMessage] = useState('')
  async function load() {
    const [courseRow, environmentRows, enrollmentRows, readinessRows] = await Promise.all([
      api(`/courses/${id}`), api(`/courses/${id}/environments`), api(`/courses/${id}/enrollments`), api(`/courses/${id}/readiness`),
    ])
    setCourse(courseRow); setEnvironments(environmentRows); setRoster(enrollmentRows); setReadiness(readinessRows)
  }
  useEffect(() => { load().catch((err) => setMessage(err.message)) }, [id])
  if (!course) return <p>{message || 'Loading course…'}</p>
  return (
    <div className="space-y-6">
      <Panel title={`${course.name} · ${course.class_code}`}>
        <form className="flex gap-2" onSubmit={async (event) => {
          event.preventDefault()
          const email = new FormData(event.target).get('email')
          try { await api(`/courses/${id}/enrollments`, { method: 'POST', body: JSON.stringify({ email }) }); event.target.reset(); await load() }
          catch (err) { setMessage(err.message) }
        }}>
          <input className={inputClass} name="email" type="email" placeholder="Student email" required />
          <button className="rounded bg-pine px-3 py-2 text-white" type="submit">Assign</button>
        </form>
        {message && <p className="mt-2 text-sm text-red-700">{message}</p>}
        <ul className="mt-4 text-sm">{roster.map((row) => <li key={row.id}>{row.name} · {row.email}</li>)}</ul>
      </Panel>
      <EnvironmentBuilder courseId={id} environments={environments} onCreated={load} />
      <Panel title="Readiness">
        {!readiness.length && <p>No enrolled students yet.</p>}
        {readiness.map((row) => (
          <div key={row.student.student_id} className="mb-3">
            <p className="font-medium">{row.student.name}</p>
            {row.environments.map((item) => <p key={item.environment_id} className="text-sm">{item.name}: {item.status} {item.summary?.results ? '' : ''}</p>)}
          </div>
        ))}
      </Panel>
    </div>
  )
}

function EnvironmentBuilder({ courseId, environments, onCreated }) {
  const [rows, setRows] = useState([{ tool: 'python', version_constraint: '==3.12.10', mandatory: true }])
  const [message, setMessage] = useState('')
  return (
    <Panel title="Environment builder">
      <ul className="mb-3">{environments.map((item) => <li key={item.id}><Link to={`/instructor/environments/${item.id}`}>{item.name}</Link></li>)}</ul>
      <form className="space-y-3" onSubmit={async (event) => {
        event.preventDefault()
        const form = new FormData(event.target)
        try {
          await api('/environments', { method: 'POST', body: JSON.stringify({ course_id: courseId, name: form.get('name'), description: form.get('description'), requirements: rows }) })
          setMessage('Draft created. Open it to publish.')
          onCreated()
        } catch (err) { setMessage(err.message) }
      }}>
        <input className={inputClass} name="name" placeholder="Environment name" required />
        <input className={inputClass} name="description" placeholder="Description" />
        {rows.map((row, index) => (
          <div key={index} className="grid gap-2 md:grid-cols-3">
            <select className={inputClass} value={row.tool} onChange={(event) => setRows(rows.map((item, itemIndex) => itemIndex === index ? { ...item, tool: event.target.value } : item))}>
              {['python', 'node', 'npm', 'git', 'docker', 'docker_engine'].map((tool) => <option key={tool}>{tool}</option>)}
            </select>
            <input className={inputClass} value={row.version_constraint} onChange={(event) => setRows(rows.map((item, itemIndex) => itemIndex === index ? { ...item, version_constraint: event.target.value } : item))} />
            <label className="text-sm"><input type="checkbox" checked={row.mandatory} onChange={(event) => setRows(rows.map((item, itemIndex) => itemIndex === index ? { ...item, mandatory: event.target.checked } : item))} /> Mandatory</label>
          </div>
        ))}
        <button type="button" onClick={() => setRows([...rows, { tool: 'git', version_constraint: '==2.56.0.3', mandatory: false }])}>Add requirement</button>
        <button className="block rounded bg-pine px-3 py-2 text-white" type="submit">Save draft</button>
      </form>
      {message && <p className="mt-2 text-sm">{message}</p>}
    </Panel>
  )
}

export function InstructorEnvironment() {
  const { id } = useParams()
  const { data, error, reload } = useLoad(() => api(`/environments/${id}`), [id])
  const [message, setMessage] = useState('')
  const [draftRows, setDraftRows] = useState(null)

  if (error) return <p>{error}</p>
  if (!data) return <p>Loading revision…</p>

  const draft = [...data.revisions].reverse().find((item) => item.publication_status === 'draft')
  const publishedRev = data.revisions.find((item) => item.id === data.current_published_revision_id)

  const activeRows = draftRows !== null
    ? draftRows
    : (draft?.specification?.requirements?.map((req) => ({
        tool: req.tool,
        version_constraint: req.version_constraint,
        mandatory: req.mandatory,
      })) || [{ tool: 'python', version_constraint: '==3.12.10', mandatory: true }])

  return (
    <Panel title={data.name}>
      <p className="mb-4 text-sm text-stone-600 dark:text-stone-300">{data.description || 'No description'}</p>
      <div className="mb-4 space-y-2 text-sm">
        <h3 className="font-medium">Revision history</h3>
        <ul className="space-y-1">
          {data.revisions.map((revision) => (
            <li key={revision.id} className="flex items-center gap-2">
              <span className="font-mono">Rev {revision.revision_number}</span>
              <StatusPill value={revision.publication_status} />
              {revision.id === data.current_published_revision_id && (
                <span className="text-xs text-pine font-medium">(Current published)</span>
              )}
            </li>
          ))}
        </ul>
      </div>

      {draft && (
        <div className="mt-4 rounded border border-stone-300 p-4 dark:border-zinc-700">
          <h3 className="font-medium mb-3">Edit draft requirements (Rev {draft.revision_number})</h3>
          <form className="space-y-3" onSubmit={async (event) => {
            event.preventDefault()
            try {
              await api(`/revisions/${draft.id}`, {
                method: 'PUT',
                body: JSON.stringify(activeRows),
              })
              setMessage('Draft updated successfully.')
              setDraftRows(null)
              reload()
            } catch (err) { setMessage(err.message) }
          }}>
            {activeRows.map((row, index) => (
              <div key={index} className="grid gap-2 md:grid-cols-4 items-center">
                <select
                  className={inputClass}
                  value={row.tool}
                  onChange={(e) => setDraftRows(activeRows.map((r, i) => i === index ? { ...r, tool: e.target.value } : r))}
                >
                  {['python', 'node', 'npm', 'git', 'docker', 'docker_engine'].map((tool) => <option key={tool}>{tool}</option>)}
                </select>
                <input
                  className={inputClass}
                  value={row.version_constraint}
                  placeholder="e.g. ==3.12.10"
                  onChange={(e) => setDraftRows(activeRows.map((r, i) => i === index ? { ...r, version_constraint: e.target.value } : r))}
                />
                <label className="text-sm flex items-center gap-1">
                  <input
                    type="checkbox"
                    checked={row.mandatory}
                    onChange={(e) => setDraftRows(activeRows.map((r, i) => i === index ? { ...r, mandatory: e.target.checked } : r))}
                  />
                  Mandatory
                </label>
                {activeRows.length > 1 && (
                  <button
                    type="button"
                    className="text-xs text-red-600 hover:underline"
                    onClick={() => setDraftRows(activeRows.filter((_, i) => i !== index))}
                  >
                    Remove
                  </button>
                )}
              </div>
            ))}
            <div className="flex gap-2 pt-2">
              <button
                type="button"
                className="rounded border border-stone-300 px-2 py-1 text-xs dark:border-zinc-700"
                onClick={() => setDraftRows([...activeRows, { tool: 'git', version_constraint: '==2.56.0.3', mandatory: false }])}
              >
                + Add tool
              </button>
              <button className="rounded bg-stone-800 px-3 py-1.5 text-xs text-white dark:bg-stone-100 dark:text-stone-900" type="submit">
                Save draft changes
              </button>
            </div>
          </form>
        </div>
      )}

      <div className="mt-6 flex gap-2">
        {draft && (
          <button
            className="rounded bg-pine px-3 py-2 text-white"
            type="button"
            onClick={async () => {
              try {
                await api(`/revisions/${draft.id}/publish`, { method: 'POST' })
                setMessage('Published draft.')
                setDraftRows(null)
                reload()
              } catch (err) { setMessage(err.message) }
            }}
          >
            Publish draft
          </button>
        )}
        <button
          type="button"
          className="rounded border px-3 py-2"
          onClick={async () => {
            try {
              await api(`/environments/${id}/revisions`, { method: 'POST' })
              setDraftRows(null)
              reload()
            } catch (err) { setMessage(err.message) }
          }}
        >
          New draft revision
        </button>
      </div>
      {message && <p className="mt-3 text-sm text-pine dark:text-pine">{message}</p>}
    </Panel>
  )
}

export function AdminHome() {
  const { data, error, reload } = useLoad(async () => ({
    pending: await api('/admin/instructor-requests'),
    users: await api('/admin/users'),
    audit: await api('/admin/audit'),
    health: await api('/health/ready'),
  }))
  if (error) return <p>{error}</p>
  if (!data) return <p>Loading administration…</p>
  return (
    <div className="space-y-6">
      <Panel title="Platform"><p>API {data.health.status} · {data.health.environment}</p></Panel>
      <Panel title="Instructor approval">
        {!data.pending.length && <p>No pending instructor requests.</p>}
        {data.pending.map((user) => (
          <div key={user.id} className="flex items-center justify-between py-2">
            <span>{user.name} · {user.email}</span>
            <span className="flex gap-2">
              <button type="button" onClick={async () => { await api(`/admin/instructors/${user.id}/approve`, { method: 'POST' }); reload() }}>Approve</button>
              <button type="button" onClick={async () => { await api(`/admin/instructors/${user.id}/reject`, { method: 'POST' }); reload() }}>Reject</button>
            </span>
          </div>
        ))}
      </Panel>
      <Panel title="Users">
        {data.users.items.map((user) => (
          <div key={user.id} className="flex items-center justify-between py-2 text-sm">
            <span>{user.name} · {user.role} · {user.account_status}</span>
            {user.account_status === 'active'
              ? <button type="button" onClick={async () => { await api(`/admin/users/${user.id}/suspend`, { method: 'POST' }); reload() }}>Suspend</button>
              : <button type="button" onClick={async () => { await api(`/admin/users/${user.id}/reactivate`, { method: 'POST' }); reload() }}>Reactivate</button>}
          </div>
        ))}
      </Panel>
      <Panel title="Audit">
        <ul className="space-y-1 text-sm font-mono">{data.audit.items.slice(0, 20).map((item) => <li key={item.id}>{item.action} · {item.outcome}</li>)}</ul>
      </Panel>
    </div>
  )
}
