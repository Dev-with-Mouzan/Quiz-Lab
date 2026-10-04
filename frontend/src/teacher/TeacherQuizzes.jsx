import React, { useState, useEffect, useCallback } from 'react'
import { quizzesAPI, coursesAPI } from '../services/api'
import EmptyState from '../components/EmptyState'
import ConfirmDialog from '../components/ConfirmDialog'
import CreateQuiz from './CreateQuiz'
import { shortDate, semLabel } from '../utils/format'
import {
  ClipboardList, HelpCircle, Plus, Trash2, Clock, CheckCircle2,
  ChevronRight, ChevronLeft, AlertTriangle, RefreshCw, GraduationCap,
  BookOpen, BadgeCheck, Shuffle, FileQuestion, X,
} from 'lucide-react'

const Chip = React.memo(function Chip({ icon: Icon, children, tone = 'default' }) {
  const tones = {
    default: 'bg-surface-50 text-navy-500 border-surface-100',
    amber: 'bg-amber-50 text-amber-700 border-amber-200',
    red: 'bg-red-50 text-red-600 border-red-200',
    green: 'bg-emerald-50 text-emerald-700 border-emerald-200',
    navy: 'bg-navy-900 text-white border-navy-950',
  }
  return (
    <span className={`inline-flex items-center gap-1.5 rounded-md border px-2 py-1 text-[11px] font-semibold ${tones[tone]}`}>
      {Icon && <Icon className="w-3.5 h-3.5" />}
      {children}
    </span>
  )
})

export default function TeacherQuizzes() {
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const [courses, setCourses] = useState([])
  const [quizzes, setQuizzes] = useState([])
  const [quizDetails, setQuizDetails] = useState({})
  const [quizAttempts, setQuizAttempts] = useState({})
  const [expandedQuiz, setExpandedQuiz] = useState(null)
  const [deleteTarget, setDeleteTarget] = useState(null)
  const [deleting, setDeleting] = useState(null)
  const [showCreate, setShowCreate] = useState(false)
  const [activeSemester, setActiveSemester] = useState(null)
  const [activeCourse, setActiveCourse] = useState(null)
  const [sessionTab, setSessionTab] = useState('morning')

  const load = useCallback(async () => {
    setLoading(true)
    setError('')
    try {
      const [q, c] = await Promise.all([quizzesAPI.list(), coursesAPI.list()])
      setQuizzes(q.data)
      setCourses(c.data)
    } catch (err) {
      console.error(err)
      setError('Could not load your quizzes. Check your connection and try again.')
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => {
    load()
  }, [load])

  const toggleQuiz = async (quiz) => {
    if (expandedQuiz === quiz.id) {
      setExpandedQuiz(null)
      return
    }
    setExpandedQuiz(quiz.id)
    if (!quizDetails[quiz.id]) {
      try {
        const [r, a] = await Promise.all([
          quizzesAPI.get(quiz.id),
          quizzesAPI.getAllAttempts(quiz.id),
        ])
        setQuizDetails((d) => ({ ...d, [quiz.id]: r.data.questions || [] }))
        setQuizAttempts((d) => ({ ...d, [quiz.id]: a.data || [] }))
      } catch {
        setQuizDetails((d) => ({ ...d, [quiz.id]: [] }))
        setQuizAttempts((d) => ({ ...d, [quiz.id]: d[quiz.id] || [] }))
      }
    }
  }

  const confirmDelete = async () => {
    if (!deleteTarget) return
    setDeleting(deleteTarget.id)
    try {
      await quizzesAPI.delete(deleteTarget.id)
      setExpandedQuiz(null)
      setQuizzes((qs) => qs.filter((q) => q.id !== deleteTarget.id))
    } catch (err) {
      window.alert(err.response?.data?.detail || 'Delete failed')
    } finally {
      setDeleting(null)
      setDeleteTarget(null)
    }
  }

  const handleCreateSuccess = () => {
    setShowCreate(false)
    load()
  }

  const goSemesters = () => {
    setActiveSemester(null)
    setActiveCourse(null)
    setExpandedQuiz(null)
    setShowCreate(false)
  }

  const goCourses = () => {
    setActiveCourse(null)
    setExpandedQuiz(null)
    setShowCreate(false)
  }

  const semesters = Object.values(
    courses.filter((c) => (c.session_type || 'morning') === sessionTab).reduce((acc, c) => {
      const key = c.semester != null ? String(c.semester) : 'other'
      if (!acc[key]) acc[key] = []
      acc[key].push(c)
      return acc
    }, {}),
  )
    .map((cs) => {
      const key = cs[0].semester != null ? String(cs[0].semester) : 'other'
      const ids = new Set(cs.map((c) => c.id))
      return {
        key,
        count: cs.length,
        session: cs.find((c) => c.session)?.session || '',
        quizCount: quizzes.filter((q) => ids.has(q.course_id)).length,
      }
    })
    .sort((a, b) => (a.key === 'other' ? 1 : b.key === 'other' ? -1 : Number(a.key) - Number(b.key)))

  const activeCourses = activeSemester != null
    ? courses.filter((c) => (c.session_type || 'morning') === sessionTab && (c.semester != null ? String(c.semester) : 'other') === activeSemester)
    : []

  const activeItems = activeCourse
    ? quizzes.filter((q) => q.course_id === activeCourse.id)
    : []

  const quizzesByCourse = quizzes.reduce((m, q) => {
    if (!m[q.course_id]) m[q.course_id] = []
    m[q.course_id].push(q)
    return m
  }, {})

  return (
    <div className="p-5 lg:p-8 max-w-4xl mx-auto">
      {/* Header */}
      <div className="text-center mb-6">
        <span className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full bg-accent-500/10 border border-accent-500/20 text-accent-600 text-[11px] font-semibold mb-3">
          <ClipboardList className="w-3 h-3" />
          Quiz Tools
        </span>
        <h1 className="text-3xl font-extrabold text-navy-900 tracking-tight">Quizzes</h1>
        <p className="text-navy-400 mt-1.5">Pick a semester and course to view its quizzes.</p>
      </div>

      {/* Loading */}
      {loading && (
        <div className="space-y-3">
          {[0, 1, 2].map((i) => (
            <div key={i} className="h-28 rounded-2xl bg-surface-200/70 animate-pulse" />
          ))}
        </div>
      )}

      {/* Error */}
      {!loading && error && (
        <div className="rounded-2xl border border-red-200 bg-red-50 px-6 py-10 text-center">
          <span className="inline-flex w-12 h-12 rounded-xl bg-red-100 items-center justify-center mb-3">
            <AlertTriangle className="w-6 h-6 text-red-500" />
          </span>
          <p className="text-sm font-medium text-red-700">{error}</p>
          <button
            onClick={load}
            className="mt-4 inline-flex items-center gap-1.5 rounded-lg bg-red-600 text-white text-xs font-semibold px-3.5 py-2 hover:bg-red-700 active:scale-[0.98] transition-all"
          >
            <RefreshCw className="w-3.5 h-3.5" />
            Try again
          </button>
        </div>
      )}

      {/* Content */}
      {!loading && !error && (
        <>
          {/* Breadcrumbs */}
          <div className="flex items-center gap-2 mb-5 text-xs flex-wrap">
            <button
              onClick={goSemesters}
              className="inline-flex items-center gap-1 font-semibold text-navy-500 hover:text-accent-600 transition-colors"
            >
              <ChevronLeft className="w-3.5 h-3.5" />
              Semesters
            </button>
            {activeSemester != null && (
              <>
                <ChevronRight className="w-3 h-3 text-navy-300" />
                <button
                  onClick={goCourses}
                  className="inline-flex items-center gap-1 font-semibold text-navy-500 hover:text-accent-600 transition-colors"
                >
                  <GraduationCap className="w-3.5 h-3.5" />
                  {activeSemester === 'other' ? 'Other' : semLabel(activeSemester)}
                </button>
              </>
            )}
            {activeCourse && (
              <>
                <ChevronRight className="w-3 h-3 text-navy-300" />
                <span className="inline-flex items-center gap-1 font-semibold text-navy-800 truncate max-w-[220px]">
                  <BookOpen className="w-3.5 h-3.5 shrink-0" />
                  {activeCourse.title}
                </span>
              </>
            )}
          </div>

          {activeSemester == null ? (
            <>
              {/* Session tabs */}
              <div className="flex justify-center mb-5">
                <div className="inline-flex gap-1 p-1 bg-surface-100 rounded-lg">
                  {[{ value: 'morning', label: 'Morning' }, { value: 'evening', label: 'Evening' }].map((r) => (
                    <button
                      key={r.value}
                      onClick={() => { setSessionTab(r.value); setActiveSemester(null); setActiveCourse(null) }}
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
              {semesters.length === 0 ? (
                <EmptyState icon={BookOpen} title={`No courses for ${sessionTab} session`} hint={`No courses assigned to the ${sessionTab} session yet.`} />
              ) : (
                <SemesterGrid semesters={semesters} onPick={setActiveSemester} />
              )}
            </>
          ) : activeCourse == null ? (
            activeCourses.length === 0 ? (
              <EmptyState icon={BookOpen} title="No courses in this semester" hint="No courses assigned to this semester yet." />
            ) : (
              <CourseGrid courses={activeCourses} quizzesByCourse={quizzesByCourse} onPick={setActiveCourse} />
            )
          ) : showCreate ? (
            <div className="relative">
              <button
                onClick={() => setShowCreate(false)}
                title="Close"
                className="absolute -top-2 -right-2 z-10 w-8 h-8 rounded-full bg-white border border-surface-200 shadow-md text-navy-400 hover:text-navy-700 flex items-center justify-center transition-colors"
              >
                <X className="w-4 h-4" />
              </button>
              <CreateQuiz
                courseId={activeCourse.id}
                onSuccess={handleCreateSuccess}
                onCancel={() => setShowCreate(false)}
              />
            </div>
          ) : (
            <>
              {/* Section header */}
              <div className="flex items-center justify-between gap-3 mb-4">
                <div className="min-w-0">
                  <p className="text-sm font-semibold text-navy-900 flex items-center gap-2">
                    <HelpCircle className="w-4 h-4 text-accent-500" />
                    Quizzes
                    <span className="text-xs font-medium text-navy-400">({activeItems.length})</span>
                  </p>
                  <p className="text-xs text-navy-400 mt-0.5">
                    Quizzes for {activeCourse.course_code}.
                  </p>
                </div>
                <button
                  onClick={() => setShowCreate(true)}
                  className="inline-flex items-center gap-1.5 rounded-lg bg-accent-500 text-white text-xs font-semibold px-3.5 py-2.5 shadow-md shadow-accent-500/20 hover:bg-accent-600 active:scale-[0.98] transition-all shrink-0"
                >
                  <Plus className="w-4 h-4" />
                  New Quiz
                </button>
              </div>

              {activeItems.length === 0 && (
                <EmptyState
                  icon={HelpCircle}
                  title="No quizzes in this course"
                  hint={`Create your first quiz for ${activeCourse.course_code}.`}
                  action={{ label: 'Create Quiz', onClick: () => setShowCreate(true) }}
                />
              )}

              {activeItems.length > 0 && (
                <div className="space-y-3">
                  {activeItems.map((q) => {
                    const questions = quizDetails[q.id] || null
                    const isOpen = expandedQuiz === q.id
                    const deadlinePast = q.deadline && new Date(q.deadline) < new Date()
                    return (
                      <div key={q.id} className="border border-surface-200 rounded-2xl bg-white p-5 hover:border-accent-200 hover:shadow-glow transition-all">
                        <div className="flex items-center gap-3.5">
                          <span className="w-11 h-11 shrink-0 rounded-xl bg-emerald-100 text-emerald-700 flex items-center justify-center">
                            <HelpCircle className="w-5 h-5" />
                          </span>
                          <div className="min-w-0 flex-1">
                            <div className="flex items-center gap-2 flex-wrap">
                              <p className="text-sm font-semibold text-navy-900 truncate">{q.title}</p>
                              {q.is_published ? (
                                <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full bg-emerald-50 text-emerald-700 border border-emerald-200 text-2xs font-bold">
                                  <BadgeCheck className="w-3 h-3" />
                                  Published
                                </span>
                              ) : (
                                <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full bg-surface-100 text-navy-400 text-2xs font-bold">
                                  <Clock className="w-3 h-3" />
                                  Draft
                                </span>
                              )}
                              {(q.question_count || 0) > (q.total_questions || 0) && (q.total_questions || 0) > 0 && (
                                <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full bg-sky-50 text-sky-700 border border-sky-200 text-2xs font-bold">
                                  <Shuffle className="w-3 h-3" />
                                  Shuffled
                                </span>
                              )}
                            </div>
                            <p className="text-xs text-navy-400 font-mono mt-0.5 truncate">
                              {q.course_code || ''} · {q.course_title || ''}
                            </p>
                          </div>
                          <button
                            onClick={() => toggleQuiz(q)}
                            className={`inline-flex items-center gap-1 rounded-lg px-3 py-1.5 text-xs font-semibold transition-colors shrink-0 ${
                              isOpen ? 'bg-navy-900 text-white' : 'bg-surface-100 text-navy-600 hover:bg-surface-200'
                            }`}
                          >
                            {isOpen ? 'Hide questions' : 'View questions'}
                            <ChevronRight className={`w-3.5 h-3.5 transition-transform ${isOpen ? 'rotate-90' : ''}`} />
                          </button>
                          <button
                            onClick={() => setDeleteTarget(q)}
                            disabled={deleting === q.id}
                            title="Delete quiz"
                            className="p-2 rounded-lg text-navy-300 hover:text-red-600 hover:bg-red-50 transition-colors shrink-0 disabled:opacity-50"
                          >
                            <Trash2 className="w-4 h-4" />
                          </button>
                        </div>

                        <div className="mt-4 flex flex-wrap items-center gap-2">
                          <Chip icon={HelpCircle}>
                            {q.question_count} question{q.question_count === 1 ? '' : 's'}
                          </Chip>
                          <Chip icon={Clock} tone={q.time_limit ? 'navy' : 'default'}>
                            {q.time_limit ? `${q.time_limit} min limit` : 'No time limit'}
                          </Chip>
                          {q.deadline && (
                            <Chip icon={Clock} tone={deadlinePast ? 'red' : 'amber'}>
                              {deadlinePast ? 'Deadline passed' : `Due ${shortDate(q.deadline)}`}
                            </Chip>
                          )}
                          <Chip tone="green">Created {shortDate(q.created_at)}</Chip>
                        </div>

                        {isOpen && (
                          <div className="mt-4 space-y-4">
                            {/* Attempts */}
                            <div className="rounded-xl bg-surface-50 border border-surface-100 p-4">
                              <p className="text-xs font-bold text-navy-700 mb-3 flex items-center gap-1.5">
                                <GraduationCap className="w-4 h-4 text-accent-500" />
                                Attempts
                              </p>
                              {!quizAttempts[q.id] ? (
                                <div className="flex items-center justify-center gap-2 py-3">
                                  <div className="w-4 h-4 animate-spin rounded-full border-2 border-accent-500 border-t-transparent" />
                                  <span className="text-xs text-navy-400">Loading attempts...</span>
                                </div>
                              ) : quizAttempts[q.id].length === 0 ? (
                                <p className="text-xs text-navy-400 text-center py-3">No attempts yet.</p>
                              ) : (
                                <div className="overflow-x-auto -mx-1">
                                  <table className="w-full text-xs">
                                    <thead>
                                      <tr className="text-left text-navy-400">
                                        <th className="font-semibold py-1.5 px-1">Student</th>
                                        <th className="font-semibold py-1.5 px-1">Score</th>
                                        <th className="font-semibold py-1.5 px-1">Percent</th>
                                        <th className="font-semibold py-1.5 px-1">Submitted</th>
                                      </tr>
                                    </thead>
                                    <tbody>
                                      {quizAttempts[q.id].map((a) => (
                                        <tr key={a.id} className="border-t border-surface-200 text-navy-700">
                                          <td className="py-2 px-1 font-semibold">{a.student_name || 'Student'}</td>
                                          <td className="py-2 px-1">{a.score}/{a.total}</td>
                                          <td className={`py-2 px-1 font-bold ${
                                            a.percentage >= 70 ? 'text-emerald-600' : a.percentage >= 40 ? 'text-amber-600' : 'text-red-500'
                                          }`}>
                                            {a.percentage}%
                                          </td>
                                          <td className="py-2 px-1 text-navy-400">{shortDate(a.submitted_at)}</td>
                                        </tr>
                                      ))}
                                    </tbody>
                                  </table>
                                </div>
                              )}
                            </div>

                            {/* Questions */}
                            <div className="rounded-xl bg-surface-50 border border-surface-100 p-4 space-y-4">
                              <p className="text-xs font-bold text-navy-700 flex items-center gap-1.5">
                                <FileQuestion className="w-4 h-4 text-accent-500" />
                                Questions
                              </p>
                              {questions && questions.length === 0 && (
                                <p className="text-xs text-navy-400 text-center">No questions in this quiz.</p>
                              )}
                            {questions && questions.length > 0 && (
                              questions.map((qu, i) => (
                                <div key={qu.id} className="rounded-lg bg-white border border-surface-100 p-3.5">
                                  <p className="text-[13px] font-semibold text-navy-900">
                                    <span className="text-accent-600 font-bold mr-1.5">Q{i + 1}.</span>
                                    {qu.text}
                                  </p>
                                  <ul className="mt-2.5 space-y-1.5">
                                    {(qu.options || []).map((opt, oi) => {
                                      const isCorrect = qu.correct_index != null && oi === qu.correct_index
                                      return (
                                        <li key={oi} className="flex items-center gap-2 text-xs">
                                          {isCorrect ? (
                                            <span className="inline-flex items-center gap-1.5 font-semibold text-emerald-700">
                                              <CheckCircle2 className="w-3.5 h-3.5" />
                                              {opt}
                                            </span>
                                          ) : (
                                            <span className="text-navy-500 pl-5">{opt}</span>
                                          )}
                                        </li>
                                      )
                                    })}
                                  </ul>
                                </div>
                              ))
                            )}
                            {!questions && (
                              <div className="flex items-center justify-center gap-2 py-3">
                                <div className="w-4 h-4 animate-spin rounded-full border-2 border-accent-500 border-t-transparent" />
                                <span className="text-xs text-navy-400">Loading questions...</span>
                              </div>
                            )}
                            </div>
                          </div>
                        )}
                      </div>
                    )
                  })}
                </div>
              )}
            </>
          )}
        </>
      )}

      <ConfirmDialog
        isOpen={!!deleteTarget}
        onClose={() => setDeleteTarget(null)}
        onConfirm={confirmDelete}
        title="Delete this quiz?"
        message={`"${deleteTarget?.title}" and all its questions and attempts will be permanently removed.`}
        loading={deleting === deleteTarget?.id}
      />
    </div>
  )
}

/* ── Sub-components ─────────────────────────────────── */

const SemesterGrid = React.memo(function SemesterGrid({ semesters, onPick }) {
  return (
    <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
      {semesters.map((s) => (
        <button
          key={s.key}
          onClick={() => onPick(s.key)}
          className="group text-left rounded-2xl border border-surface-200 bg-white p-5 transition-all duration-200 hover:border-accent-300 hover:shadow-elevated"
        >
          <div className="flex items-start justify-between gap-3">
            <span className="w-11 h-11 rounded-xl bg-navy-900 text-white flex items-center justify-center">
              <GraduationCap className="w-5 h-5" />
            </span>
            <span className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full bg-accent-500/10 text-accent-600 text-2xs font-bold">
              <HelpCircle className="w-3 h-3" />
              {s.quizCount} quiz{s.quizCount === 1 ? '' : 'zes'}
            </span>
          </div>
          <h3 className="mt-4 text-lg font-bold text-navy-900 group-hover:text-accent-600 transition-colors">
            {s.key === 'other' ? 'Other' : semLabel(s.key)}
          </h3>
          {s.session && <p className="text-xs text-navy-400 mt-0.5">Session {s.session}</p>}
          <div className="mt-4 flex items-center gap-4 text-xs text-navy-500">
            <span className="tabular-nums"><span className="font-bold text-navy-900">{s.count}</span> courses</span>
            <span className="tabular-nums"><span className="font-bold text-navy-900">{s.quizCount}</span> quizzes</span>
          </div>
          <div className="mt-4 flex items-center gap-1 text-xs font-semibold text-accent-600">
            Manage quizzes
            <ChevronRight className="w-3.5 h-3.5 group-hover:translate-x-0.5 transition-transform" />
          </div>
        </button>
      ))}
    </div>
  )
})

const CourseGrid = React.memo(function CourseGrid({ courses, quizzesByCourse, onPick }) {
  return (
    <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
      {courses.map((c) => {
        const quizCount = (quizzesByCourse[c.id] || []).length
        return (
          <button
            key={c.id}
            onClick={() => onPick(c)}
            className="group text-left rounded-2xl border border-surface-200 bg-white p-5 transition-all duration-200 hover:border-accent-300 hover:shadow-elevated"
          >
            <div className="flex items-start justify-between gap-3">
              <span className="w-11 h-11 rounded-xl bg-navy-800 text-white flex items-center justify-center">
                <BookOpen className="w-5 h-5" />
              </span>
              {c.session && (
                <span className="inline-flex items-center px-2.5 py-1 rounded-full bg-surface-100 text-navy-500 text-2xs font-bold">
                  {c.session}
                </span>
              )}
            </div>
            <p className="mt-4 text-[11px] font-bold text-accent-600 tracking-wider uppercase">{c.course_code}</p>
            <h3 className="mt-0.5 text-sm font-bold text-navy-900 leading-snug group-hover:text-accent-600 transition-colors">
              {c.title}
            </h3>
            <div className="mt-4 flex items-center gap-4 text-xs text-navy-500 flex-wrap">
              <span className="tabular-nums"><span className="font-bold text-navy-900">{quizCount}</span> quizzes</span>
            </div>
            <div className="mt-4 flex items-center gap-1 text-xs font-semibold text-accent-600">
              View quizzes
              <ChevronRight className="w-3.5 h-3.5 group-hover:translate-x-0.5 transition-transform" />
            </div>
          </button>
        )
      })}
    </div>
  )
})
