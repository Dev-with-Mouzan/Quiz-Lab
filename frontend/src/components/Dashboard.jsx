import { AlertTriangle, RefreshCw } from 'lucide-react'

export function DashboardHero({ dateLine, firstName, subtitle, chipIcon: ChipIcon, chipText, stats }) {
  return (
    <section className="relative overflow-hidden rounded-2xl bg-navy-950 text-white p-6 lg:p-8 mb-6">
      <div className="absolute -top-20 -right-16 w-72 h-72 rounded-full bg-accent-500/20 blur-3xl pointer-events-none" />
      <div className="absolute -bottom-28 -left-12 w-80 h-80 rounded-full bg-accent-500/10 blur-3xl pointer-events-none" />
      <div
        className="absolute inset-0 opacity-[0.05] pointer-events-none"
        style={{
          backgroundImage: 'radial-gradient(circle at 1px 1px, #fff 1px, transparent 0)',
          backgroundSize: '22px 22px',
        }}
      />

      <div className="relative flex flex-col md:flex-row md:items-center gap-6">
        <div className="flex-1 min-w-0">
          <p className="text-xs font-medium text-accent-300">{dateLine}</p>
          <h1 className="mt-2 text-2xl lg:text-[28px] font-bold tracking-tight leading-tight">
            Welcome back, <span className="text-accent-400">{firstName}</span>
          </h1>
          <p className="mt-1.5 text-sm text-navy-300">{subtitle}</p>
          <div className="mt-4 inline-flex items-center gap-2 rounded-full border border-white/10 bg-white/5 px-3 py-1.5">
            <ChipIcon className="w-3.5 h-3.5 text-accent-400" />
            <span className="text-[11px] font-medium text-navy-200">{chipText}</span>
          </div>
        </div>

        <div className="grid grid-cols-2 gap-2.5 w-full md:w-[320px] shrink-0">
          {stats.map((s) => (
            <div key={s.label} className="rounded-xl border border-white/10 bg-white/5 px-4 py-3">
              <p className={`text-xl font-bold tabular-nums tracking-tight ${s.tone || ''}`}>{s.value}</p>
              <p className="text-[11px] font-medium text-navy-300 mt-0.5">
                {s.label}
                {s.note ? <span className="text-navy-400"> · {s.note}</span> : null}
              </p>
            </div>
          ))}
        </div>
      </div>
    </section>
  )
}

export function Section({ icon: Icon, iconClass, title, subtitle, right, children, className = '' }) {
  return (
    <section className={`flex-1 rounded-2xl border border-surface-200 bg-white p-5 ${className}`}>
      <div className="flex items-center justify-between gap-3">
        <div className="min-w-0">
          <h2 className="text-sm font-semibold text-navy-900 flex items-center gap-2">
            <span className={`w-7 h-7 rounded-lg flex items-center justify-center shrink-0 ${iconClass}`}>
              <Icon className="w-3.5 h-3.5" />
            </span>
            {title}
          </h2>
          {subtitle && <p className="text-xs text-navy-400 mt-1">{subtitle}</p>}
        </div>
        {right}
      </div>
      {children}
    </section>
  )
}

export function ProgressRing({ pct, tone, value, sub }) {
  return (
    <div className="mt-5 flex items-center justify-center gap-7">
      <div className="relative w-28 h-28 shrink-0">
        <svg viewBox="0 0 120 120" className="w-full h-full -rotate-90">
          <circle cx="60" cy="60" r="52" fill="none" strokeWidth="10" className="stroke-surface-100" />
          <circle
            cx="60"
            cy="60"
            r="52"
            fill="none"
            strokeWidth="10"
            strokeLinecap="round"
            className={tone}
            strokeDasharray="326.73"
            strokeDashoffset={326.73 * (1 - Math.min(pct, 100) / 100)}
          />
        </svg>
        <div className="absolute inset-0 flex items-center justify-center">
          <span className={`text-xl font-bold tabular-nums ${tone.replace('stroke-', 'text-')}`}>
            {pct > 0 ? `${pct.toFixed(0)}%` : '—'}
          </span>
        </div>
      </div>
      <div className="min-w-0">{sub}</div>
    </div>
  )
}

export function DashboardLoading() {
  return (
    <div className="p-5 lg:p-8 max-w-6xl mx-auto w-full">
      <div className="h-44 rounded-2xl bg-surface-200/70 animate-pulse mb-6" />
      <div className="grid lg:grid-cols-[1.55fr_1fr] gap-5">
        <div className="space-y-5">
          <div className="h-64 rounded-2xl bg-surface-200/70 animate-pulse" />
          <div className="h-72 rounded-2xl bg-surface-200/70 animate-pulse" />
        </div>
        <div className="space-y-5">
          <div className="h-56 rounded-2xl bg-surface-200/70 animate-pulse" />
          <div className="h-40 rounded-2xl bg-surface-200/70 animate-pulse" />
        </div>
      </div>
    </div>
  )
}

export function DashboardError({ onRetry, message = 'Could not load your dashboard data. Check your connection and try again.' }) {
  return (
    <div className="p-5 lg:p-8 max-w-6xl mx-auto w-full">
      <div className="rounded-2xl border border-red-200 bg-red-50 px-6 py-10 text-center">
        <span className="inline-flex w-12 h-12 rounded-xl bg-red-100 items-center justify-center mb-3">
          <AlertTriangle className="w-6 h-6 text-red-500" />
        </span>
        <p className="text-sm font-medium text-red-700">{message}</p>
        <button
          onClick={onRetry}
          className="mt-4 inline-flex items-center gap-1.5 rounded-lg bg-red-600 text-white text-xs font-semibold px-3.5 py-2 hover:bg-red-700 active:scale-[0.98] transition-all"
        >
          <RefreshCw className="w-3.5 h-3.5" />
          Try again
        </button>
      </div>
    </div>
  )
}
