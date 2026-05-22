import { useEffect, useRef } from 'react'
import { API_BASE } from '../api/client'

// ---------------------------------------------------------------------------
// useAudio — score announcement, bust sound, and win fanfare
//
// Preloads HTMLAudioElement instances for all scores 0–180 and named sounds
// (gewonnen.mp3) on first mount.
// Guarantees no overlap: any currently playing sound is stopped before a new
// one starts. Missing files are handled gracefully (console.warn only).
// ---------------------------------------------------------------------------

export function useAudio(): {
  playScore: (total: number) => void
  playBust: () => void
  playWin: () => void
} {
  // Map from score value → preloaded Audio element
  const audioMapRef = useRef<Map<number, HTMLAudioElement>>(new Map())
  // Named sounds: "gewonnen" etc.
  const namedRef = useRef<Map<string, HTMLAudioElement>>(new Map())
  // Currently playing Audio element (if any)
  const currentRef = useRef<HTMLAudioElement | null>(null)

  useEffect(() => {
    const base = `${API_BASE}/sounds`
    const map = audioMapRef.current
    for (let i = 0; i <= 180; i++) {
      const audio = new Audio(`${base}/${i}.mp3`)
      audio.preload = 'auto'
      audio.onerror = () => {
        console.warn(`[useAudio] Missing sound file: ${i}.mp3`)
      }
      map.set(i, audio)
    }

    const named = namedRef.current
    for (const name of ['gewonnen']) {
      const audio = new Audio(`${base}/${name}.mp3`)
      audio.preload = 'auto'
      audio.onerror = () => {
        console.warn(`[useAudio] Missing sound file: ${name}.mp3`)
      }
      named.set(name, audio)
    }

    return () => {
      // Stop playback on unmount
      if (currentRef.current) {
        currentRef.current.pause()
        currentRef.current = null
      }
    }
  }, [])

  function play(audio: HTMLAudioElement | undefined): void {
    if (!audio) {
      console.warn('[useAudio] Sound not available')
      return
    }
    // Cancel any currently playing sound
    if (currentRef.current && currentRef.current !== audio) {
      currentRef.current.pause()
      currentRef.current.currentTime = 0
    }
    currentRef.current = audio
    audio.currentTime = 0
    audio.play()?.catch((err: unknown) => {
      console.warn('[useAudio] Playback failed:', err)
    })
  }

  function playScore(total: number): void {
    play(audioMapRef.current.get(total))
  }

  // Bust sound: 0.mp3 (also the "0 points" announcement; used for both cases)
  function playBust(): void {
    play(audioMapRef.current.get(0))
  }

  // Win fanfare: played when a match is finished
  function playWin(): void {
    play(namedRef.current.get('gewonnen'))
  }

  return { playScore, playBust, playWin }
}
