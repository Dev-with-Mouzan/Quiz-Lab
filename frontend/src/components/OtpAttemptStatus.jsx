import { Clock } from 'lucide-react'
import { formatMMSS } from '../hooks/useOtpAttempts'

// Shows how many OTP guesses are left in the current round, or the lock countdown.
export default function OtpAttemptStatus({ isLocked, lockRemaining, attemptsLeft, maxAttempts }) {
  if (isLocked) {
    return (
      <div className="flex items-start gap-3 bg-danger-light text-danger-dark px-4 py-3 rounded-xl text-sm font-medium border border-danger/20">
        <Clock className="w-4 h-4 mt-0.5 shrink-0" />
        <p>
          OTP entry is locked after too many wrong codes. You can try again in{' '}
          <span className="font-mono font-bold">{formatMMSS(lockRemaining)}</span>.
        </p>
      </div>
    )
  }

  if (attemptsLeft === null || attemptsLeft === undefined) return null

  const used = maxAttempts - attemptsLeft
  return (
    <div className="flex items-center justify-between gap-3 text-sm">
      <p className={`font-semibold ${attemptsLeft <= 1 ? 'text-danger-dark' : 'text-navy-600'}`}>
        {attemptsLeft} {attemptsLeft === 1 ? 'attempt' : 'attempts'} left
      </p>
      <div className="flex items-center gap-1.5" aria-label={`${used} of ${maxAttempts} attempts used`}>
        {Array.from({ length: maxAttempts }).map((_, i) => (
          <span
            key={i}
            className={`w-2.5 h-2.5 rounded-full ${i < used ? 'bg-danger' : 'bg-accent-400'}`}
          />
        ))}
      </div>
    </div>
  )
}
