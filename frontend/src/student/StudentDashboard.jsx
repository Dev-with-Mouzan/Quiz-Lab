import { useState, useEffect, useCallback } from 'react'
import { Link } from 'react-router-dom'
import { useAuth } from '../context/AuthContext'
import { coursesAPI, quizzesAPI } from '../services/api'
import {
  DashboardHero, DashboardLoading, DashboardError, Section, ProgressRing,
} from '../components/Dashboard'
import EmptyState from '../components/EmptyState'
import { shortDate, MONTHS } from '../utils/format'
import {
  BookOpen, CalendarClock, CheckCircle2, ChevronRight, CalendarCheck,
  GraduationCap, Award, Lock, FileQuestion,
} from 'lucide-react'

const pctOf = (score, total) => (total > 0 ? Math.round((score / total) * 100) : 0)
const scoreTone = (pct) => (pct >= 70 ? 'text-emerald-600' : pct >= 40 ? 'text-amber-600' : 'text-red-500')

export default function StudentDashboard() {
  const { user } = useAuth()
  const [courses, setCourses] = useState([])
  const [quizzes, setQuizzes] = useState([])
  const [attempts, setAttempts] = useState({})
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)

  const load = useCallback(async () => {
    setLoading(true)
    setError(null)
    try {
      const [c, q] = await Promise.all([coursesAPI.list(), quizzesAPI.list()])
      setCourses(c.data)
      setQuizzes(q.data)

      const settled = await Promise.allSettled(q.data.map((quiz) => quizzesAPI.getAttempt(quiz.id)))
      const map = {}
      q.data.forEach((quiz, i) => {
        const r = settled[i]
        map[quiz.id] = r.status === 'fulfilled' && r.value.data ? r.value.data : null
      })
      setAttempts(map)
    } catch (err) {
      console.error(err)
      setError('Could not load your dashboard data. Check your connection and try again.')
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => {
    load()
  }, [load])

  if (loading) return <DashboardLoading />
  if (error) return <DashboardError onRetry={load} message={error} />

  const firstName = user?.first_name || 'there'
  const semester = user?.semester
  const dateLine = new Date().toLocaleDateString('en-US', {
    weekday: 'long', day: 'numeric', month: 'long', year: 'numeric',
  })
  const now = new Date()

  const completed = quizzes.filter((q) => attempts[q.id])
  const open = quizzes.filter((q) => !attempts[q.id] && !(q.deadline && new Date(q.deadline) < now))
  const expired = quizzes.filter((q) => !attempts[q.id] && q.deadline && new Date(q.deadline) < now)
  const avgPct = completed.length > 0
    ? Math.round(completed.reduce((sum, q) => sum + pctOf(attempts[q.id].score, attempts[q.id].total), 0) / completed.length)
    : 0

  const upcoming = open
    .filter((q) => q.deadline)
    .sort((x, y) => new Date(x.deadline) - new Date(y.deadline))

  const completionPct = quizzes.length > 0 ? (completed.length / quizzes.length) * 100 : 0

  const courseStats = (courseId) => {
    const list = quizzes.filter((q) => q.course_id === courseId)
    const done = list.filter((q) => attempts[q.id])
    return {
      total: list.length,
      done: done.length,
      pct: list.length > 0 ? (done.length / list.length) * 100 : 0,
    }
  }

  const recentResults = [...completed]
    .filter((q) => attempts[q.id]?.submitted_at)
    .sort((x, y) => new Date(attempts[y.id].submitted_at) - new Date(attempts[x.id].submitted_at))
    .slice(0, 3)

  const heroStats = [
    { label: 'Courses', value: courses.length },
    { label: 'Open', value: open.length, note: 'quizzes' },
    { label: 'Completed', value: completed.length },
    { label: 'Avg score', value: completed.length > 0 ? `${avgPct}%` : '—', tone: completed.length > 0 ? scoreTone(avgPct) : '' },
  ]

  return (
    <div className="p-5 lg:p-8 max-w-6xl mx-auto w-full">
      <DashboardHero
        dateLine={dateLine}
        firstName={firstName}
        subtitle={`${semester ? `Semester ${semester} · BSCS` : 'BSCS'} student — here's how your quizzes are going.`}
        chipIcon={GraduationCap}
        chipText={
          open.length === 0
            ? 'All clear — nothing waiting on you'
            : `${open.length} quiz${open.length === 1 ? '' : 'zes'} awaiting completion`
        }
        stats={heroStats}
      />

      <div className="grid lg:grid-cols-[1.55fr_1fr] gap-5">
        {/* Left column */}
        <div className="flex flex-col gap-5 min-w-0">
          <Section
            icon={CalendarClock}
            iconClass="bg-amber-100 text-amber-700"
            title="Upcoming deadlines"
            subtitle={
              upcoming.length > 2
                ? `Showing 2 of ${upcoming.length} — nearest deadlines first.`
                : 'Deadlines in the order they hit.'
            }
            right={
              upcoming.length > 0 && (
                <Link to="/student/quizzes" className="inline-flex items-center gap-1 text-xs font-semibold text-accent-600 hover:text-accent-700 whitespace-nowrap">
                  All quizzes <ChevronRight className="w-3.5 h-3.5" />
                </Link>
              )
            }
          >
            {upcoming.length === 0 ? (
              <div className="mt-5">
                <EmptyState compact icon={CheckCircle2} title="No deadlines waiting" hint="You're all caught up on timed quizzes." />
              </div>
            ) : (
              <div className="mt-4 space-y-2.5">
                {upcoming.slice(0, 2).map((quiz) => {
                  const d = new Date(quiz.deadline)
                  const daysLeft = Math.ceil((d - now) / (1000 * 60 * 60 * 24))
                  const chip =
                    daysLeft <= 2
                      ? 'bg-red-50 text-red-600 border-red-200'
                      : daysLeft <= 7
                        ? 'bg-amber-50 text-amber-700 border-amber-200'
                        : 'bg-surface-100 text-navy-500 border-surface-200'
                  return (
                    <Link
                      key={quiz.id}
                      to="/student/quizzes"
                      className="group flex items-center gap-3.5 rounded-xl border border-surface-100 bg-surface-50/70 p-3 transition-all duration-200 hover:border-accent-200 hover:bg-white"
                    >
                      <span className="flex w-11 shrink-0 flex-col items-center rounded-lg bg-white border border-surface-200 py-1.5">
                        <span className="text-[9px] font-bold uppercase tracking-wider text-navy-400">
                          {MONTHS[d.getMonth()]}
                        </span>
                        <span className="text-base font-bold leading-tight text-navy-900 tabular-nums">{d.getDate()}</span>
                      </span>
                      <div className="min-w-0 flex-1">
                        <p className="text-sm font-medium text-navy-900 truncate">{quiz.title}</p>
                        <p className="text-[11px] text-navy-400 truncate">{quiz.course_code || 'Quiz'}</p>
                      </div>
                      <span className={`shrink-0 rounded-md border px-2 py-0.5 text-[10px] font-semibold ${chip}`}>
                        {daysLeft <= 0 ? 'Due today' : `${daysLeft}d left`}
                      </span>
                      <ChevronRight className="w-4 h-4 shrink-0 text-navy-300 transition-all group-hover:text-accent-500 group-hover:translate-x-0.5" />
                    </Link>
                  )
                })}
              </div>
            )}
            {upcoming.length > 2 && (
              <Link
                to="/student/quizzes"
                className="mt-3.5 flex items-center justify-center gap-1.5 rounded-xl border border-dashed border-surface-200 py-2.5 text-xs font-semibold text-navy-500 transition-all hover:border-accent-300 hover:text-accent-600 hover:bg-accent-500/5 active:scale-[0.99]"
              >
                See all deadlines
                <span className="text-navy-400 font-medium tabular-nums">({upcoming.length - 2} more)</span>
                <ChevronRight className="w-3.5 h-3.5" />
              </Link>
            )}
          </Section>

          <Section
            icon={BookOpen}
            iconClass="bg-navy-900 text-white"
            title="My courses"
            subtitle={
              courses.length > 2
                ? `Progress across all ${courses.length} semester courses.`
                : 'Current semester courses.'
            }
            right={
              <span className="text-xs font-medium text-navy-400 tabular-nums">{courses.length} active</span>
            }
          >
            {courses.length === 0 ? (
              <div className="mt-5">
                <EmptyState compact icon={BookOpen} title="No courses available yet" hint="Your semester courses will show up here." />
              </div>
            ) : (
              <div className="mt-4 space-y-3">
                {courses.map((course) => {
                  const m = courseStats(course.id)
                  const tone =
                    m.pct >= 75 ? { text: 'text-emerald-600', bar: 'bg-emerald-500' }
                    : m.pct >= 50 ? { text: 'text-amber-600', bar: 'bg-amber-500' }
                    : { text: 'text-red-500', bar: 'bg-red-500' }
                  return (
                    <div key={course.id} className="rounded-xl border border-surface-200 hover:border-accent-300 p-3.5 transition-colors">
                      <div className="flex items-center gap-3">
                        <span className="w-10 h-10 shrink-0 rounded-xl flex items-center justify-center text-xs font-bold bg-gradient-to-br from-navy-800 to-navy-950 text-white">
                          {course.course_code.slice(0, 2).toUpperCase()}
                        </span>
                        <div className="min-w-0 flex-1">
                          <p className="text-sm font-medium truncate text-navy-900">{course.title}</p>
                          <p className="text-[11px] text-navy-400 font-mono truncate">
                            {course.course_code}
                            {course.session ? ` · ${course.session}` : ''}
                          </p>
                        </div>
                        <div className="text-right shrink-0">
                          <p className={`text-lg font-bold tabular-nums leading-none ${m.total > 0 ? tone.text : 'text-navy-400'}`}>
                            {m.pct.toFixed(0)}
                            <span className="text-[11px] font-semibold text-navy-400">%</span>
                          </p>
                          <p className="text-[10px] text-navy-400 mt-1 tabular-nums">
                            {m.done}/{m.total} quizzes
                          </p>
                        </div>
                      </div>
                      <div className="mt-3 h-1.5 w-full rounded-full bg-surface-100 overflow-hidden">
                        <div
                          className={`h-full rounded-full transition-all duration-700 ${m.total > 0 ? tone.bar : 'bg-navy-300'}`}
                          style={{ width: `${Math.min(m.pct, 100)}%` }}
                        />
                      </div>
                    </div>
                  )
                })}
              </div>
            )}
          </Section>
        </div>

        {/* Right rail */}
        <div className="flex flex-col gap-5 min-w-0">
          <Section
            icon={CalendarCheck}
            iconClass="bg-sky-100 text-sky-700"
            title="Completion"
            subtitle={`${quizzes.length} quiz${quizzes.length === 1 ? '' : 'zes'} assigned`}
          >
            <ProgressRing
              pct={completionPct}
              tone={completionPct >= 100 && quizzes.length > 0 ? 'stroke-emerald-500' : 'stroke-accent-500'}
              sub={
                <>
                  <p className="text-2xl font-bold text-navy-900 tabular-nums">{completed.length}</p>
                  <p className="text-[11px] text-navy-400">quizzes completed</p>
                  <p className="text-[11px] text-navy-400 mt-0.5">
                    <span className={`font-semibold tabular-nums ${open.length > 0 ? 'text-amber-600' : 'text-navy-600'}`}>
                      {open.length}
                    </span>{' '}
                    still open
                    {expired.length > 0 ? (
                      <>
                        {' · '}
                        <span className="font-semibold text-red-500 tabular-nums">{expired.length}</span> expired
                      </>
                    ) : null}
                  </p>
                </>
              }
            />
            <div className="mt-5 flex items-center justify-between rounded-xl bg-surface-50 px-3.5 py-2.5">
              <p className="text-[11px] text-navy-500">
                {quizzes.length === 0
                  ? 'No quizzes assigned yet.'
                  : open.length === 0
                    ? 'Everything assigned is done — nice work.'
                    : `${open.length} to go before the deadlines hit.`}
              </p>
              <Link to="/student/quizzes" className="inline-flex items-center gap-0.5 text-[11px] font-semibold text-accent-600 hover:text-accent-700 shrink-0">
                Quizzes <ChevronRight className="w-3 h-3" />
              </Link>
            </div>
          </Section>

          <Section
            icon={Award}
            iconClass="bg-amber-100 text-amber-700"
            title="Recent results"
            subtitle="Your latest scored attempts."
            right={
              recentResults.length > 0 && (
                <Link to="/student/quizzes" className="inline-flex items-center gap-0.5 text-[11px] font-semibold text-accent-600 hover:text-accent-700">
                  View all <ChevronRight className="w-3 h-3" />
                </Link>
              )
            }
          >
            {recentResults.length === 0 ? (
              <div className="mt-5">
                <EmptyState compact title="Nothing scored yet" hint="Your results appear after you submit a quiz." />
              </div>
            ) : (
              <div className="mt-3 space-y-1">
                {recentResults.map((quiz) => {
                  const a = attempts[quiz.id]
                  const pct = pctOf(a.score, a.total)
                  return (
                    <Link
                      key={quiz.id}
                      to="/student/quizzes"
                      className="group flex items-center gap-3 rounded-xl p-2.5 transition-colors hover:bg-surface-50"
                    >
                      <span className={`shrink-0 rounded-md px-2 py-0.5 text-[10px] font-bold ${
                        pct >= 70 ? 'bg-emerald-100 text-emerald-700' : pct >= 40 ? 'bg-amber-100 text-amber-700' : 'bg-red-100 text-red-600'
                      }`}>
                        {pct}%
                      </span>
                      <div className="min-w-0 flex-1">
                        <p className="text-[13px] font-medium text-navy-900 truncate">{quiz.title}</p>
                        <p className="text-[10px] text-navy-400 truncate">
                          {quiz.course_code || 'Quiz'} · {shortDate(a.submitted_at)}
                        </p>
                      </div>
                      <span className={`shrink-0 text-[11px] font-bold tabular-nums ${scoreTone(pct)}`}>
                        {a.score}/{a.total}
                      </span>
                      <ChevronRight className="w-3.5 h-3.5 shrink-0 text-navy-300 group-hover:text-accent-500 group-hover:translate-x-0.5 transition-all" />
                    </Link>
                  )
                })}
              </div>
            )}
          </Section>

          {expired.length > 0 && (
            <Section icon={Lock} iconClass="bg-surface-200 text-navy-500" title="Expired" subtitle="Deadlines that have passed.">
              <div className="mt-3 space-y-1">
                {expired.slice(0, 3).map((quiz) => (
                  <div key={quiz.id} className="flex items-center gap-3 rounded-xl p-2.5 bg-surface-50/70">
                    <FileQuestion className="w-4 h-4 text-navy-300 shrink-0" />
                    <div className="min-w-0 flex-1">
                      <p className="text-[13px] font-medium text-navy-500 truncate">{quiz.title}</p>
                      <p className="text-[10px] text-navy-400 truncate">{quiz.course_code || 'Quiz'}</p>
                    </div>
                    <span className="shrink-0 rounded-md border border-red-200 bg-red-50 px-2 py-0.5 text-[10px] font-semibold text-red-600">
                      Expired
                    </span>
                  </div>
                ))}
              </div>
            </Section>
          )}
        </div>
      </div>
    </div>
  )
}
