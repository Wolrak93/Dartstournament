import { renderHook, act } from '@testing-library/react'
import { beforeEach, afterEach, describe, expect, it, vi } from 'vitest'
import { useAudio } from '../hooks/useAudio'

// ---------------------------------------------------------------------------
// Mock api/client so API_BASE resolves to a known value
// ---------------------------------------------------------------------------

vi.mock('../api/client', () => ({
  API_BASE: 'http://localhost:8000',
  WS_BASE: 'ws://localhost:8000',
  playerPhotoUrl: (path: string) => `http://localhost:8000/static/${path}`,
}))

// ---------------------------------------------------------------------------
// Mock HTMLAudioElement using a proper constructor function so that
// vi.stubGlobal works correctly and jsdom's real Audio is not used.
// ---------------------------------------------------------------------------

interface AudioInstance {
  src: string
  preload: string
  currentTime: number
  play: ReturnType<typeof vi.fn>
  pause: ReturnType<typeof vi.fn>
  onerror: (() => void) | null
}

let audioInstances: AudioInstance[]

beforeEach(() => {
  audioInstances = []

  // Use a regular function (not an arrow function) so it can act as a constructor.
  const AudioMock = vi.fn(function (this: AudioInstance, src: string) {
    this.src = src
    this.preload = 'none'
    this.currentTime = 0
    this.play = vi.fn().mockResolvedValue(undefined)
    this.pause = vi.fn()
    this.onerror = null
    audioInstances.push(this)
  })

  vi.stubGlobal('Audio', AudioMock)
})

afterEach(() => {
  vi.unstubAllGlobals()
})

// ---------------------------------------------------------------------------
// Tests
// ---------------------------------------------------------------------------

describe('useAudio', () => {
  it('preloads audio elements for scores 0–180 and named sounds on mount', () => {
    renderHook(() => useAudio())

    // 181 score files (0–180) + 1 named file (gewonnen)
    expect(audioInstances).toHaveLength(182)
    expect(audioInstances.some((a) => a.src.endsWith('/180.mp3'))).toBe(true)
    expect(audioInstances.some((a) => a.src.endsWith('/0.mp3'))).toBe(true)
    expect(audioInstances.some((a) => a.src.endsWith('/gewonnen.mp3'))).toBe(true)
  })

  it('playWin plays gewonnen.mp3', () => {
    const { result } = renderHook(() => useAudio())

    act(() => {
      result.current.playWin()
    })

    const audioWin = audioInstances.find((a) => a.src.endsWith('/gewonnen.mp3'))
    expect(audioWin).toBeDefined()
    expect(audioWin!.play).toHaveBeenCalledTimes(1)
  })

  it('sets preload to auto for all preloaded files', () => {
    renderHook(() => useAudio())

    expect(audioInstances.every((a) => a.preload === 'auto')).toBe(true)
  })

  it('playScore(180) plays the correct audio file', () => {
    const { result } = renderHook(() => useAudio())

    act(() => {
      result.current.playScore(180)
    })

    const audio180 = audioInstances.find((a) => a.src.endsWith('/180.mp3'))
    expect(audio180).toBeDefined()
    expect(audio180!.play).toHaveBeenCalledTimes(1)
  })

  it('playBust plays 0.mp3', () => {
    const { result } = renderHook(() => useAudio())

    act(() => {
      result.current.playBust()
    })

    const audio0 = audioInstances.find((a) => a.src.endsWith('/0.mp3'))
    expect(audio0).toBeDefined()
    expect(audio0!.play).toHaveBeenCalledTimes(1)
  })

  it('second playScore call pauses the first before starting the second', () => {
    const { result } = renderHook(() => useAudio())

    act(() => {
      result.current.playScore(100)
    })

    const audio100 = audioInstances.find((a) => a.src.endsWith('/100.mp3'))!
    expect(audio100.play).toHaveBeenCalledTimes(1)
    expect(audio100.pause).not.toHaveBeenCalled()

    act(() => {
      result.current.playScore(60)
    })

    // First audio must have been paused before the second started
    expect(audio100.pause).toHaveBeenCalledTimes(1)

    const audio60 = audioInstances.find((a) => a.src.endsWith('/60.mp3'))!
    expect(audio60.play).toHaveBeenCalledTimes(1)
  })

  it('playing the same audio twice does not call pause on itself', () => {
    const { result } = renderHook(() => useAudio())

    act(() => {
      result.current.playScore(50)
    })
    act(() => {
      result.current.playScore(50)
    })

    const audio50 = audioInstances.find((a) => a.src.endsWith('/50.mp3'))!
    // Same audio object: currentRef === audio, so pause must NOT be called
    expect(audio50.pause).not.toHaveBeenCalled()
  })
})
