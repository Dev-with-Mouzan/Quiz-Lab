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
  BookOpen, CalendarClock, CheckCircle2, ChevronRight, PlusCircle,
  GraduationCap, HelpCircle, Inbox, Award, FileSpreadsheet,
} from 'lucide-react'

const MAX_ATTEMPT_FETCHES = 15

export default function TeacherDashboard() {
  const { user } = useAuth()
  const [courses, setCourses] = useState([])
  const [quizzes, setQuizzes] = useState([])
  const [attemptsByQuiz, setAttemptsByQuiz] = useState({})
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)
  const [sessionTab, setSessionTab] = useState('morning')

  const load = useCallback(async () => {
    setLoading(true)
    setError(null)
    try {
      const [c, q] = await Promise.all([coursesAPI.list(), quizzesAPI.list()])
      setCourses(c.data)
      setQuizzes(q.data)

      const recent = q.data.slice(0, MAX_ATTEMPT_FETCHES)
      const settled = await Promise.allSettled(recent.map((quiz) => quizzesAPI.getAllAttempts(quiz.id)))
      const map = {}
      recent.forEach((quiz, i) => {
        const r = settled[i]
        map[quiz.id] = r.status === 'fulfilled' ? (r.value.data || []) : []
      })
      setAttemptsByQuiz(map)
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
  const dateLine = new Date().toLocaleDateString('en-US', {
    weekday: 'long', day: 'numeric', month: 'long', year: 'numeric',
  })

  const now = new Date()
  const upcoming = quizzes
    .filter((q) => q.deadline && new Date(q.deadline) >= now)
    .sort((x, y) => new Date(x.deadline) - new Date(y.deadline))
  const published = quizzes.filter((q) => q.is_published).length

  const displayedCourses = courses.filter((c) => (c.session_type || 'morning') === sessionTab)

  const courseStats = (courseId) => {
    const list = quizzes.filter((q) => q.course_id === courseId)
    return {
      total: list.length,
      published: list.filter((q) => q.is_published).length,
      attempts: list.reduce((sum, q) => sum + (attemptsByQuiz[q.id]?.length || 0), 0),
      drafts: list.filter((q) => !q.is_published).length,
    }
  }

  const allAttempts = Object.entries(attemptsByQuiz).flatMap(([quizId, list]) => {
    const quiz = quizzes.find((q) => q.id === quizId)
    return list.map((a) => ({ ...a, quizTitle: quiz?.title || 'Quiz', courseCode: quiz?.course_code }))
  })
  const totalAttempts = allAttempts.length
  const withAttempts = Object.values(attemptsByQuiz).filter((l) => l.length > 0).length
  const coveredPct = published > 0 ? Math.min(withAttempts, published) / published * 100 : 0
  const recentAttempts = [...allAttempts]
    .filter((a) => a.submitted_at)
    .sort((x, y) => new Date(y.submitted_at) - new Date(x.submitted_at))
    .slice(0, 3)

  const heroStats = [
    { label: 'Active courses', value: courses.length },
    { label: 'Quizzes', value: quizzes.length },
    { label: 'Upcoming', value: upcoming.length, note: 'deadlines' },
    { label: 'Published', value: published },
  ]

  const quickActions = [
    { to: '/teacher/create-quiz', icon: PlusCircle, label: 'Create quiz', desc: 'DOCX/CSV bank or manual questions', color: 'bg-accent-500' },
    { to: '/teacher/quizzes', icon: HelpCircle, label: 'All quizzes', desc: 'Attempts, scores and deletes', color: 'bg-navy-950' },
  ]

  return (
    <div className="p-5 lg:p-8 max-w-6xl mx-auto w-full">
      <DashboardHero
        dateLine={dateLine}
        firstName={firstName}
        subtitle="Faculty · CS Dept — here's how your quizzes are doing."
        chipIcon={GraduationCap}
        chipText={
          upcoming.length === 0
            ? 'No deadlines on the horizon'
            : `${upcoming.length} deadline${upcoming.length === 1 ? '' : 's'} coming up`
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
                <Link to="/teacher/quizzes" className="inline-flex items-center gap-1 text-xs font-semibold text-accent-600 hover:text-accent-700 whitespace-nowrap">
                  All quizzes <ChevronRight className="w-3.5 h-3.5" />
                </Link>
              )
            }
          >
            {upcoming.length === 0 ? (
              <div className="mt-5">
                <EmptyState compact icon={CheckCircle2} title="No upcoming deadlines" hint="Create a quiz to keep students working." />
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
                      to="/teacher/quizzes"
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
                to="/teacher/quizzes"
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
              displayedCourses.length > 2
                ? `Showing all ${displayedCourses.length} ${sessionTab} courses.`
                : `${sessionTab.charAt(0).toUpperCase() + sessionTab.slice(1)} courses you teach.`
            }
            right={
              <span className="text-xs font-medium text-navy-400 tabular-nums">{displayedCourses.length} courses</span>
            }
          >
            <div className="mt-4 flex justify-center">
              <div className="inline-flex gap-1 p-1 bg-surface-100 rounded-lg">
                {[{ value: 'morning', label: 'Morning' }, { value: 'evening', label: 'Evening' }].map((r) => (
                  <button
                    key={r.value}
                    onClick={() => setSessionTab(r.value)}
                    className={`px-5 py-1.5 rounded-md text-xs font-semibold transition-all whitespace-nowrap ${
                      sessionTab === r.value
                        ? 'bg-gradient-to-r from-amber-400 to-amber-500 text-navy-900 shadow-sm shadow-amber-400/20'
                        : 'text-navy-400 hover:text-navy-600'
                    }`}
                  >
                    {r.label}
                  </button>
                ))}
              </div>
            </div>

            {displayedCourses.length === 0 ? (
              <div className="mt-5">
                <EmptyState compact icon={BookOpen} title={`No courses for ${sessionTab} session`} hint={`No courses assigned to the ${sessionTab} session yet.`} />
              </div>
            ) : (
              <div className="mt-4 grid grid-cols-1 sm:grid-cols-2 gap-4">
                {displayedCourses.map((course) => {
                  const m = courseStats(course.id)
                  return (
                    <div key={course.id} className="group border border-surface-200 bg-white hover:border-accent-300 rounded-2xl overflow-hidden transition-all">
                      <div className="flex items-center justify-between gap-3 px-5 py-3 bg-navy-950">
                        <span className="inline-flex items-center gap-1.5 text-[11px] font-bold text-white">
                          <GraduationCap className="w-3.5 h-3.5 text-accent-400" />
                          BSCS
                        </span>
                        <span className="inline-flex items-center px-2.5 py-0.5 rounded-md text-[11px] font-bold font-mono tracking-wide bg-white/10 border border-white/10 text-accent-300">
                          {course.session || '—'}
                        </span>
                      </div>
                      <div className="p-5">
                        <div className="flex items-center gap-3">
                          <span className="w-11 h-11 shrink-0 rounded-xl bg-navy-800 text-white group-hover:bg-accent-500 transition-colors flex items-center justify-center text-xs font-bold">
                            {course.course_code.slice(0, 2).toUpperCase()}
                          </span>
                          <div className="min-w-0 flex-1">
                            <p className="text-sm font-semibold truncate text-navy-900 group-hover:text-accent-600 transition-colors">{course.title}</p>
                            <p className="text-xs text-navy-400 font-mono mt-0.5">
                              {course.course_code}
                              {course.semester ? ` · Sem ${course.semester}` : ''}
                            </p>
                          </div>
                        </div>

                        <div className="mt-4 grid grid-cols-3 gap-2">
                          <div className="rounded-lg bg-surface-50 border border-surface-100 px-2 py-2.5 text-center">
                            <HelpCircle className="w-3.5 h-3.5 text-navy-300 mx-auto" />
                            <p className="text-sm font-bold text-navy-900 tabular-nums mt-1">{m.total}</p>
                            <p className="text-[9px] text-navy-400 mt-0.5">Quizzes</p>
                          </div>
                          <div className="rounded-lg bg-surface-50 border border-surface-100 px-2 py-2.5 text-center">
                            <FileSpreadsheet className="w-3.5 h-3.5 text-navy-300 mx-auto" />
                            <p className="text-sm font-bold text-navy-900 tabular-nums mt-1">{m.published}</p>
                            <p className="text-[9px] text-navy-400 mt-0.5">Published</p>
                          </div>
                          <div className="rounded-lg bg-surface-50 border border-surface-100 px-2 py-2.5 text-center">
                            <Inbox className="w-3.5 h-3.5 text-navy-300 mx-auto" />
                            <p className="text-sm font-bold text-navy-900 tabular-nums mt-1">{m.attempts}</p>
                            <p className="text-[9px] text-navy-400 mt-0.5">Attempts</p>
                          </div>
                        </div>

                        {m.drafts > 0 && (
                          <Link
                            to="/teacher/quizzes"
                            className="mt-2.5 flex items-center justify-between gap-2 rounded-lg bg-amber-50 border border-amber-200 px-3 py-2 transition-colors hover:bg-amber-100/70"
                          >
                            <span className="text-[11px] font-semibold text-amber-700">
                              {m.drafts} draft{m.drafts === 1 ? '' : 's'} not published
                            </span>
                            <span className="inline-flex items-center gap-0.5 text-[11px] font-bold text-accent-600">
                              Review <ChevronRight className="w-3 h-3" />
                            </span>
                          </Link>
                        )}
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
            icon={Inbox}
            iconClass="bg-emerald-100 text-emerald-700"
            title="Attempts"
            subtitle={`${totalAttempts} attempt${totalAttempts === 1 ? '' : 's'} received`}
          >
            <ProgressRing
              pct={coveredPct}
              tone={withAttempts >= published && published > 0 ? 'stroke-emerald-500' : 'stroke-accent-500'}
              sub={
                <>
                  <p className="text-2xl font-bold text-navy-900 tabular-nums">{totalAttempts}</p>
                  <p className="text-[11px] text-navy-400">attempts received</p>
                  <p className="text-[11px] text-navy-400 mt-0.5">
                    <span className="font-semibold text-navy-600 tabular-nums">{withAttempts}</span> of{' '}
                    <span className="font-semibold text-navy-600 tabular-nums">{published}</span> published quizzes
                  </p>
                </>
              }
            />
            <div className="mt-5 flex items-center justify-between rounded-xl bg-surface-50 px-3.5 py-2.5">
              <p className="text-[11px] text-navy-500">
                {published === 0
                  ? 'Publish a quiz to start collecting attempts.'
                  : withAttempts >= published
                    ? 'Every published quiz has responses.'
                    : 'Some published quizzes have no attempts yet.'}
              </p>
              <Link to="/teacher/quizzes" className="inline-flex items-center gap-0.5 text-[11px] font-semibold text-accent-600 hover:text-accent-700 shrink-0">
                View <ChevronRight className="w-3 h-3" />
              </Link>
            </div>
          </Section>

          <Section
            icon={Award}
            iconClass="bg-amber-100 text-amber-700"
            title="Recent attempts"
            subtitle="Latest submissions across your quizzes."
            right={
              recentAttempts.length > 0 && (
                <Link to="/teacher/quizzes" className="inline-flex items-center gap-0.5 text-[11px] font-semibold text-accent-600 hover:text-accent-700">
                  View all <ChevronRight className="w-3 h-3" />
                </Link>
              )
            }
          >
            {recentAttempts.length === 0 ? (
              <div className="mt-5">
                <EmptyState compact title="No attempts yet" hint="Student submissions will appear here." />
              </div>
            ) : (
              <div className="mt-3 space-y-1">
                {recentAttempts.map((a) => (
                  <Link
                    key={`${a.id}-${a.quizTitle}`}
                    to="/teacher/quizzes"
                    className="group flex items-center gap-3 rounded-xl p-2.5 transition-colors hover:bg-surface-50"
                  >
                    <span className={`shrink-0 rounded-md px-2 py-0.5 text-[10px] font-bold ${
                      a.percentage >= 70 ? 'bg-emerald-100 text-emerald-700' : a.percentage >= 40 ? 'bg-amber-100 text-amber-700' : 'bg-red-100 text-red-600'
                    }`}>
                      {a.percentage}%
                    </span>
                    <div className="min-w-0 flex-1">
                      <p className="text-[13px] font-medium text-navy-900 truncate">{a.student_name}</p>
                      <p className="text-[10px] text-navy-400 truncate">
                        {a.quizTitle} · {shortDate(a.submitted_at)}
                      </p>
                    </div>
                    <ChevronRight className="w-3.5 h-3.5 shrink-0 text-navy-300 group-hover:text-accent-500 group-hover:translate-x-0.5 transition-all" />
                  </Link>
                ))}
              </div>
            )}
          </Section>

          <Section icon={PlusCircle} iconClass="bg-sky-100 text-sky-700" title="Quick actions" className="p-2">
            {quickActions.map((action) => (
              <Link
                key={action.label}
                to={action.to}
                className="group flex items-center gap-3.5 rounded-xl p-3 transition-colors hover:bg-accent-500/5"
              >
                <span className={`w-10 h-10 rounded-xl flex items-center justify-center text-white shrink-0 ${action.color} shadow-md`}>
                  <action.icon className="w-5 h-5" />
                </span>
                <div className="min-w-0 flex-1">
                  <p className="text-sm font-semibold text-navy-900 group-hover:text-accent-600 transition-colors">{action.label}</p>
                  <p className="text-[11px] text-navy-400">{action.desc}</p>
                </div>
                <ChevronRight className="w-4 h-4 shrink-0 text-navy-300 group-hover:text-accent-500 group-hover:translate-x-0.5 transition-all" />
              </Link>
            ))}
          </Section>
        </div>
      </div>
    </div>
  )
}
