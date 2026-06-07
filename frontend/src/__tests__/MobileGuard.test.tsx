import { render, screen } from '@testing-library/react'
import { MemoryRouter, Route, Routes } from 'react-router-dom'
import { describe, expect, it, vi } from 'vitest'

vi.mock('../mobile/mobileAuth', () => ({
  isLoggedIn: vi.fn(),
}))

import { isLoggedIn } from '../mobile/mobileAuth'
import MobileGuard from '../mobile/MobileGuard'

describe('MobileGuard', () => {
  it('redirects to /mobile/login when not logged in', () => {
    vi.mocked(isLoggedIn).mockReturnValue(false)

    render(
      <MemoryRouter initialEntries={['/mobile']}>
        <Routes>
          <Route path="/mobile/login" element={<div>Login Page</div>} />
          <Route element={<MobileGuard />}>
            <Route path="/mobile" element={<div>Protected Content</div>} />
          </Route>
        </Routes>
      </MemoryRouter>,
    )

    expect(screen.getByText('Login Page')).toBeInTheDocument()
    expect(screen.queryByText('Protected Content')).not.toBeInTheDocument()
  })

  it('renders child route when logged in', () => {
    vi.mocked(isLoggedIn).mockReturnValue(true)

    render(
      <MemoryRouter initialEntries={['/mobile']}>
        <Routes>
          <Route path="/mobile/login" element={<div>Login Page</div>} />
          <Route element={<MobileGuard />}>
            <Route path="/mobile" element={<div>Protected Content</div>} />
          </Route>
        </Routes>
      </MemoryRouter>,
    )

    expect(screen.getByText('Protected Content')).toBeInTheDocument()
    expect(screen.queryByText('Login Page')).not.toBeInTheDocument()
  })
})
