import { useState, useEffect, useCallback } from 'react'

// Tracks the OTP guess budget for one email: attempts left in this round, and the
// lock countdown after a round is used up. The server decides the numbers, and the
// lock end time is kept in localStorage so a page refresh doesn't unlock the input.

const DEFAULT_MAX = 3
const lockKey = (email) => `otpLockUntil:${email}`

function readLock(email) {
  try {
    const until = Number(localStorage.getItem(lockKey(email)))
    return until > Date.now() ? until : null
  } catch {
    return null
  }
}

function writeLock(email, until) {
  try {
    if (until) localStorage.setItem(lockKey(email), String(until))
    else localStorage.removeItem(lockKey(email))
  } catch {
    // Storage can be unavailable (private mode); the in-memory state still works.
  }
}

export function useOtpAttempts(email) {
  const [maxAttempts, setMaxAttempts] = useState(DEFAULT_MAX)
  const [attemptsLeft, setAttemptsLeft] = useState(null) // null = no wrong guess yet
  const [lockUntil, setLockUntil] = useState(null)
  const [now, setNow] = useState(() => Date.now())

  // Restore a lock when the email is known (it may arrive after first render)
  useEffect(() => {
    setLockUntil(email ? readLock(email) : null)
    setNow(Date.now())
  }, [email])

  // Tick once a second while locked; when the lock ends, start a fresh round
  useEffect(() => {
    if (!lockUntil) return undefined
    const id = setInterval(() => {
      const t = Date.now()
      setNow(t)
      if (t >= lockUntil) {
        setLockUntil(null)
        setAttemptsLeft(null)
        writeLock(email, null)
      }
    }, 1000)
    return () => clearInterval(id)
  }, [lockUntil, email])

  // Call with the error from a failed OTP request. Returns the message to show.
  const handleOtpError = useCallback((err) => {
    const data = err?.response?.data || {}
    if (typeof data.max_attempts === 'number') setMaxAttempts(data.max_attempts)
    if (typeof data.attempts_left === 'number') setAttemptsLeft(data.attempts_left)
    if (typeof data.locked_seconds === 'number' && data.locked_seconds > 0) {
      const until = Date.now() + data.locked_seconds * 1000
      setNow(Date.now())
      setLockUntil(until)
      writeLock(email, until)
    }
    return data.detail || 'Invalid OTP code'
  }, [email])

  const lockRemaining = lockUntil ? Math.max(0, Math.ceil((lockUntil - now) / 1000)) : 0

  return {
    isLocked: lockRemaining > 0,
    lockRemaining,        // seconds
    attemptsLeft,         // null until the first wrong guess
    maxAttempts,
    handleOtpError,
  }
}

export function formatMMSS(totalSeconds) {
  const m = String(Math.floor(totalSeconds / 60)).padStart(2, '0')
  const s = String(totalSeconds % 60).padStart(2, '0')
  return `${m}:${s}`
}
