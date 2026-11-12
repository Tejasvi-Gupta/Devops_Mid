import { createElement } from 'react'
import { render, screen } from '@testing-library/react'
import { PlanPreview } from '../ui'
import { homeFor } from '../auth'

test('routes each role to its home', () => {
  expect(homeFor(null)).toBe('/login')
  expect(homeFor({ role: 'student', account_status: 'active' })).toBe('/student')
  expect(homeFor({ role: 'instructor', instructor_status: 'pending', account_status: 'active' })).toBe('/account')
  expect(homeFor({ role: 'instructor', instructor_status: 'approved', account_status: 'active' })).toBe('/instructor')
  expect(homeFor({ role: 'admin', account_status: 'active' })).toBe('/admin')
})

test('shows a plan before installation', () => {
  render(createElement(PlanPreview, {
    plan: { actions: [{ id: '1', tool: 'git', operation: 'install', reason: 'Git is missing', impact: 'Installs Git 2.56.0.3', version: '2.56.0.3' }], uncertainties: [] },
  }))
  expect(screen.getByText('Git is missing')).toBeTruthy()
  expect(screen.getByText('Target 2.56.0.3')).toBeTruthy()
})
