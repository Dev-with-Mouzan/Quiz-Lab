import { useState, useEffect, useCallback } from 'react'
import { Link } from 'react-router-dom'
import { usersAPI, coursesAPI, quizzesAPI } from '../services/api'
import { useAuth } from '../context/AuthContext'
import { DashboardHero, DashboardLoading, DashboardError, Section } from '../components/Dashboard'
import {
  Users, GraduationCap, Clock, BookOpen, ClipboardList,
  ChevronRight, UserCog,
} from 'lucide-react'

const ROLE_CHIP = {
  admin: 'bg-navy-900 text-white',
  teacher: 'bg-sky-100 text-sky-700',
  student: 'bg-emerald-100 text-emerald-700',
}

export default function AdminDashboard() {
  const { user } = useAuth()
  const [stats, setStats] = useState(null)
  const [courses, setCourses] = useState([])
  const [quizzes, setQuizzes] = useState([])
  const [users, setUsers] = useState([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)

  const load = useCallback(async () => {
    setLoading(true)
    setError(null)
    try {
      const [s, c, q, u] = await Promise.all([
        usersAPI.getStats(),
        coursesAPI.list(),
        quizzesAPI.list(),
        usersAPI.list(),
      ])
      setStats(s.data)
      setCourses(c.data)
      setQuizzes(q.data)
      setUsers(u.data)
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

  const firstName = user?.first_name || 'Admin'
  const dateLine = new Date().toLocaleDateString('en-US', {
    weekday: 'long', day: 'numeric', month: 'long', year: 'numeric',
  })

  const pending = stats?.pending_verification || 0
  const newest = [...users].sort((a, b) => b.id - a.id).slice(0, 5)
  const published = quizzes.filter((q) => q.is_published).length

  const heroStats = [
    { label: 'Total users', value: stats?.total_users ?? '—' },
    { label: 'Students', value: stats?.total_students ?? '—' },
    { label: 'Teachers', value: stats?.total_teachers ?? '—' },
    { label: 'Pending OTP', value: pending, tone: pending > 0 ? 'text-amber-400' : '' },
  ]

  const hub = [
    {
      to: '/admin/users', icon: Users, label: 'Manage Users',
      desc: 'Create teachers, verify and edit accounts.', color: 'bg-navy-950 text-accent-400',
    },
    {
      to: '/admin/courses', icon: BookOpen, label: 'Manage Courses',
      desc: 'Courses assigned to teachers — quizzes attach to these.', color: 'bg-navy-950 text-accent-400',
    },
  ]

  return (
    <div className="p-5 lg:p-8 max-w-6xl mx-auto w-full">
      <DashboardHero
        dateLine={dateLine}
        firstName={firstName}
        subtitle="CS Dept · GGC Burewala — keeping users, courses and quizzes in sync."
        chipIcon={UserCog}
        chipText={
          pending === 0
            ? 'All accounts verified'
            : `${pending} account${pending === 1 ? '' : 's'} pending email verification`
        }
        stats={heroStats}
      />

      <div className="grid lg:grid-cols-[1.55fr_1fr] gap-5">
        {/* Left column */}
        <div className="flex flex-col gap-5 min-w-0">
          <Section
            icon={UserCog}
            iconClass="bg-navy-900 text-white"
            title="Management"
            subtitle="The two places admin work lives."
          >
            <div className="mt-4 grid grid-cols-1 sm:grid-cols-2 gap-4">
              {hub.map((h) => (
                <Link
                  key={h.to}
                  to={h.to}
                  className="group rounded-xl border border-surface-200 p-4 hover:border-accent-300 hover:bg-accent-500/5 transition-all"
                >
                  <span className={`w-10 h-10 rounded-xl flex items-center justify-center ${h.color}`}>
                    <h.icon className="w-5 h-5" />
                  </span>
                  <p className="mt-3 text-sm font-semibold text-navy-900 group-hover:text-accent-600 transition-colors">
                    {h.label}
                  </p>
                  <p className="text-[11px] text-navy-400 mt-0.5">{h.desc}</p>
                  <span className="mt-2 inline-flex items-center gap-0.5 text-[11px] font-bold text-accent-600">
                    Open <ChevronRight className="w-3 h-3" />
                  </span>
                </Link>
              ))}
            </div>
          </Section>

          <Section
            icon={Users}
            iconClass="bg-accent-100 text-accent-700"
            title="Newest users"
            subtitle={`${users.length} account${users.length === 1 ? '' : 's'} total — newest first.`}
            right={
              <Link to="/admin/users" className="inline-flex items-center gap-1 text-xs font-semibold text-accent-600 hover:text-accent-700 whitespace-nowrap">
                All users <ChevronRight className="w-3.5 h-3.5" />
              </Link>
            }
          >
            {newest.length === 0 ? (
              <p className="mt-4 text-xs text-navy-400">No accounts yet.</p>
            ) : (
              <div className="mt-3 space-y-1">
                {newest.map((u) => {
                  const role = u.role?.name || 'student'
                  const full = `${u.first_name || ''} ${u.last_name || ''}`.trim() || u.email
                  return (
                    <Link
                      key={u.id}
                      to="/admin/users"
                      className="group flex items-center gap-3 rounded-xl p-2.5 transition-colors hover:bg-surface-50"
                    >
                      <span className="w-9 h-9 shrink-0 rounded-full bg-navy-900 text-white flex items-center justify-center text-xs font-bold">
                        {(u.first_name?.[0] || '?')}{u.last_name?.[0] || ''}
                      </span>
                      <div className="min-w-0 flex-1">
                        <p className="text-[13px] font-medium text-navy-900 truncate">{full}</p>
                        <p className="text-[10px] text-navy-400 truncate">{u.email}</p>
                      </div>
                      <span className={`shrink-0 rounded-md px-2 py-0.5 text-[10px] font-bold capitalize ${ROLE_CHIP[role] || ROLE_CHIP.student}`}>
                        {role}
                      </span>
                      <span className={`shrink-0 rounded-md border px-2 py-0.5 text-[10px] font-semibold ${
                        u.is_verified
                          ? 'bg-emerald-50 text-emerald-700 border-emerald-200'
                          : 'bg-amber-50 text-amber-700 border-amber-200'
                      }`}>
                        {u.is_verified ? 'Verified' : 'Pending'}
                      </span>
                      <ChevronRight className="w-3.5 h-3.5 shrink-0 text-navy-300 group-hover:text-accent-500 group-hover:translate-x-0.5 transition-all" />
                    </Link>
                  )
                })}
              </div>
            )}
          </Section>
        </div>

        {/* Right rail */}
        <div className="flex flex-col gap-5 min-w-0">
          <Section
            icon={ClipboardList}
            iconClass="bg-amber-100 text-amber-700"
            title="System overview"
            subtitle="What the quiz feature is running on."
          >
            <div className="mt-4 space-y-2">
              <Link
                to="/admin/courses"
                className="group flex items-center justify-between rounded-xl border border-surface-100 bg-surface-50/70 px-3.5 py-3 transition-all hover:border-accent-200 hover:bg-white"
              >
                <span className="inline-flex items-center gap-2.5 text-sm font-medium text-navy-900">
                  <BookOpen className="w-4 h-4 text-navy-400" />
                  Courses
                </span>
                <span className="inline-flex items-center gap-1 text-sm font-bold tabular-nums text-navy-900">
                  {courses.length}
                  <ChevronRight className="w-3.5 h-3.5 text-navy-300 group-hover:text-accent-500 transition-colors" />
                </span>
              </Link>
              <div className="flex items-center justify-between rounded-xl border border-surface-100 bg-surface-50/70 px-3.5 py-3">
                <span className="inline-flex items-center gap-2.5 text-sm font-medium text-navy-900">
                  <ClipboardList className="w-4 h-4 text-navy-400" />
                  Quizzes
                </span>
                <span className="text-sm font-bold tabular-nums text-navy-900">{quizzes.length}</span>
              </div>
              <div className="flex items-center justify-between rounded-xl border border-surface-100 bg-surface-50/70 px-3.5 py-3">
                <span className="inline-flex items-center gap-2.5 text-sm font-medium text-navy-900">
                  <GraduationCap className="w-4 h-4 text-navy-400" />
                  Published
                </span>
                <span className="text-sm font-bold tabular-nums text-emerald-600">
                  {published}
                  <span className="text-xs font-semibold text-navy-400"> / {quizzes.length}</span>
                </span>
              </div>
            </div>
            <p className="mt-3.5 text-[11px] text-navy-400 leading-relaxed">
              Students only see published quizzes. Drafts stay private to their teacher.
            </p>
          </Section>

          <Section
            icon={Clock}
            iconClass="bg-sky-100 text-sky-700"
            title="Verification"
            subtitle="Email OTP keeps accounts real."
          >
            <div className="mt-4 flex items-center justify-between rounded-xl bg-surface-50 px-3.5 py-3">
              <p className="text-[11px] text-navy-500">
                {pending > 0
                  ? `${pending} user${pending === 1 ? '' : 's'} haven't confirmed their email yet.`
                  : 'Every account has confirmed its email.'}
              </p>
              <Link to="/admin/users" className="inline-flex items-center gap-0.5 text-[11px] font-semibold text-accent-600 hover:text-accent-700 shrink-0">
                Review <ChevronRight className="w-3 h-3" />
              </Link>
            </div>
            <div className="mt-3 grid grid-cols-2 gap-2">
              <div className="rounded-xl bg-surface-50 px-3 py-2.5 text-center">
                <p className="text-lg font-bold text-navy-900 tabular-nums">{stats?.total_users ?? '—'}</p>
                <p className="text-[10px] text-navy-400 mt-0.5">Registered</p>
              </div>
              <div className="rounded-xl bg-surface-50 px-3 py-2.5 text-center">
                <p className="text-lg font-bold text-navy-900 tabular-nums">{courses.length}</p>
                <p className="text-[10px] text-navy-400 mt-0.5">Courses</p>
              </div>
            </div>
          </Section>
        </div>
      </div>
    </div>
  )
}
