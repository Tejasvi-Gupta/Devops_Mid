import React from 'react'
import { Navigate, Route, Routes } from 'react-router-dom'
import { homeFor, useAuth } from './auth'
import { AccessDenied, AccountPage, AdminHome, DevicePage, InstructorCourse, InstructorEnvironment, InstructorHome, JobPage, LoginPage, NotificationsPage, RegisterPage, StudentEnvironment, StudentHome } from './screens'
import { Shell } from './ui'

function Guard({ children, allow }) {
  const { user, ready } = useAuth()
  if (!ready) return <p className="p-8">Loading session…</p>
  if (!user) return <Navigate to="/login" replace />
  if (allow && !allow(user)) return <Navigate to="/access-denied" replace />
  return children
}

export default function App() {
  const { ready, user } = useAuth()
  return (
    <Shell>
      <Routes>
        <Route path="/login" element={ready && user ? <Navigate to={homeFor(user)} replace /> : <LoginPage />} />
        <Route path="/register" element={<RegisterPage />} />
        <Route path="/access-denied" element={<AccessDenied />} />
        <Route path="/account" element={<Guard><AccountPage /></Guard>} />
        <Route path="/notifications" element={<Guard><NotificationsPage /></Guard>} />
        <Route path="/student" element={<Guard allow={(user) => user.role === 'student'}><StudentHome /></Guard>} />
        <Route path="/student/device" element={<Guard allow={(user) => user.role === 'student'}><DevicePage /></Guard>} />
        <Route path="/student/environments/:id" element={<Guard allow={(user) => user.role === 'student'}><StudentEnvironment /></Guard>} />
        <Route path="/student/jobs/:id" element={<Guard allow={(user) => user.role === 'student'}><JobPage /></Guard>} />
        <Route path="/instructor" element={<Guard allow={(user) => user.role === 'instructor' && user.instructor_status === 'approved'}><InstructorHome /></Guard>} />
        <Route path="/instructor/courses/:id" element={<Guard allow={(user) => user.role === 'instructor' && user.instructor_status === 'approved'}><InstructorCourse /></Guard>} />
        <Route path="/instructor/environments/:id" element={<Guard allow={(user) => user.role === 'instructor' && user.instructor_status === 'approved'}><InstructorEnvironment /></Guard>} />
        <Route path="/admin" element={<Guard allow={(user) => user.role === 'admin'}><AdminHome /></Guard>} />
        <Route path="*" element={<Navigate to={user ? homeFor(user) : '/login'} replace />} />
      </Routes>
    </Shell>
  )
}
