import { beforeEach, describe, expect, it } from 'vitest'
import {
  clearToken,
  getStoredPlayerId,
  getToken,
  isLoggedIn,
  setToken,
} from '../mobile/mobileAuth'

describe('mobileAuth', () => {
  beforeEach(() => {
    localStorage.clear()
  })

  it('getToken returns null when no token is set', () => {
    expect(getToken()).toBeNull()
  })

  it('setToken stores the token and getToken retrieves it', () => {
    setToken('abc123')
    expect(getToken()).toBe('abc123')
  })

  it('isLoggedIn returns false without a token', () => {
    expect(isLoggedIn()).toBe(false)
  })

  it('isLoggedIn returns true after setToken', () => {
    setToken('tok')
    expect(isLoggedIn()).toBe(true)
  })

  it('setToken with playerId stores the player id', () => {
    setToken('tok', 42)
    expect(getStoredPlayerId()).toBe(42)
  })

  it('getStoredPlayerId returns null when not set', () => {
    expect(getStoredPlayerId()).toBeNull()
  })

  it('clearToken removes token and player id', () => {
    setToken('tok', 5)
    clearToken()
    expect(getToken()).toBeNull()
    expect(getStoredPlayerId()).toBeNull()
    expect(isLoggedIn()).toBe(false)
  })
})
