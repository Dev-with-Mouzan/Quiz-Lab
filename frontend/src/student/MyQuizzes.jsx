import { useState, useEffect, useRef } from 'react'
import { Link } from 'react-router-dom'
import { quizzesAPI } from '../services/api'
import EmptyState from '../components/EmptyState'
import {
  ClipboardList, HelpCircle, ChevronLeft, ChevronRight, ChevronDown, BookOpen,
  FileQuestion, CheckCircle2, X, Shuffle, AlertTriangle, Timer,
} from 'lucide-react'

export default function MyQuizzes() {
  const [quizzes, setQuizzes] = useState([])
  const [loading, setLoading] = useState(true)
  const [activeCourseId, setActiveCourseId] = useState(null)

  useEffect(() => {
    quizzesAPI.list()
      .then((r) => setQuizzes(Array.isArray(r.data) ? r.data : []))
      .catch(() => setQuizzes([]))
      .finally(() => setLoading(false))
  }, [])

  const courseMap = {}
  quizzes.forEach((q) => {
    if (!courseMap[q.course_id]) {
      courseMap[q.course_id] = {
        id: q.course_id,
        title: q.course_title || 'Course',
        code: q.course_code || '',
        quizzes: [],
      }
    }
    courseMap[q.course_id].quizzes.push(q)
  })
  const courses = Object.values(courseMap).sort((x, y) => (x.title || '').localeCompare(y.title || ''))
  const activeCourse = courses.find((c) => c.id === activeCourseId) || null

  return (
    <div className="p-5 lg:p-8 max-w-5xl mx-auto w-full">
      {/* Header */}
      <div className="text-center mb-6">
        <span className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full bg-accent-500/10 border border-accent-500/20 text-accent-600 text-[11px] font-semibold mb-3">
          <ClipboardList className="w-3 h-3" />
          Quiz Hub
        </span>
        <h1 className="text-3xl font-extrabold text-navy-900 tracking-tight">Quizzes</h1>
        <p className="text-navy-400 mt-1.5">Pick a subject to see its quizzes.</p>
      </div>

      {loading ? (
        <div className="min-h-[220px] flex items-center justify-center">
          <div className="w-10 h-10 border-2 border-surface-200 border-t-accent-500 rounded-full animate-spin" />
        </div>
      ) : (
        <>
          {/* Breadcrumbs */}
          <div className="flex items-center gap-2 mb-5 text-xs flex-wrap">
            <button
              onClick={() => setActiveCourseId(null)}
              className="inline-flex items-center gap-1 font-semibold text-navy-500 hover:text-accent-600 transition-colors"
            >
              <ChevronLeft className="w-3.5 h-3.5" />
              Subjects
            </button>
            {activeCourse && (
              <>
                <ChevronRight className="w-3 h-3 text-navy-300" />
                <span className="inline-flex items-center gap-1 font-semibold text-navy-800 truncate max-w-[260px]">
                  <BookOpen className="w-3.5 h-3.5 shrink-0" />
                  {activeCourse.title}
                </span>
              </>
            )}
          </div>

          {!activeCourse ? (
            courses.length === 0 ? (
              <EmptyState
                icon={HelpCircle}
                title="No quizzes published for any of your subjects yet."
                hint="They will appear here once your teachers publish them."
              />
            ) : (
              <SubjectGrid courses={courses} onPick={setActiveCourseId} />
            )
          ) : (
            <div className="space-y-3">
              {activeCourse.quizzes.map((q) => <QuizCard key={q.id} quiz={q} />)}
            </div>
          )}
        </>
      )}

      <div className="flex justify-center mt-8">
        <Link to="/student" className="inline-flex items-center gap-2 px-4 py-2 rounded-xl text-xs font-semibold text-navy-500 hover:text-navy-900 border border-surface-200 bg-white transition-colors">
          <ChevronLeft className="w-3.5 h-3.5" />
          Back to Dashboard
        </Link>
      </div>
    </div>
  )
}

/* ── Subject grid ────────────────────────────────────── */

function SubjectGrid({ courses, onPick }) {
  return (
    <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
      {courses.map((c) => {
        const totalQuestions = c.quizzes.reduce((n, q) => n + (q.question_count || 0), 0)
        return (
          <button
            key={c.id}
            onClick={() => onPick(c.id)}
            className="group text-left rounded-2xl border border-surface-200 bg-white p-5 transition-all duration-200 hover:border-accent-300 hover:shadow-elevated"
          >
            <div className="flex items-start justify-between gap-3">
              <span className="w-11 h-11 rounded-xl bg-navy-800 text-white flex items-center justify-center">
                <BookOpen className="w-5 h-5" />
              </span>
            </div>
            <p className="mt-4 text-[11px] font-bold text-accent-600 tracking-wider uppercase">{c.code}</p>
            <h3 className="mt-0.5 text-sm font-bold text-navy-900 leading-snug group-hover:text-accent-600 transition-colors">
              {c.title}
            </h3>
            <div className="mt-4 flex items-center gap-2 text-xs flex-wrap">
              <span className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full bg-surface-100 text-navy-600 text-2xs font-bold">
                <HelpCircle className="w-3 h-3" />
                {c.quizzes.length} quiz{c.quizzes.length === 1 ? '' : 'zes'}
              </span>
              {totalQuestions > 0 && (
                <span className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full bg-surface-100 text-navy-600 text-2xs font-bold">
                  <FileQuestion className="w-3 h-3" />
                  {totalQuestions} questions
                </span>
              )}
            </div>
            <div className="mt-4 flex items-center gap-1 text-xs font-semibold text-accent-600">
              Open quizzes
              <ChevronRight className="w-3.5 h-3.5 group-hover:translate-x-0.5 transition-transform" />
            </div>
          </button>
        )
      })}
    </div>
  )
}

/* ── Quiz card (take / result) ───────────────────────── */

function QuizCard({ quiz }) {
  const [expanded, setExpanded] = useState(false)
  const [detail, setDetail] = useState(null)
  const [loadingDetail, setLoadingDetail] = useState(false)
  const [answers, setAnswers] = useState({})
  const [submitting, setSubmitting] = useState(false)
  const [result, setResult] = useState(null)
  const [error, setError] = useState('')
  const [secondsLeft, setSecondsLeft] = useState(null)
  const answersRef = useRef(answers)
  answersRef.current = answers
  const autoSubmittedRef = useRef(false)

  const toggle = async () => {
    const next = !expanded
    setExpanded(next)
    if (next && !detail && !result) {
      setLoadingDetail(true)
      setError('')
      try {
        const [r, attemptRes] = await Promise.all([
          quizzesAPI.get(quiz.id),
          quizzesAPI.getAttempt(quiz.id),
        ])
        setDetail(r.data)
        setResult(attemptRes.data)
      } catch (err) {
        setDetail((prev) => prev ?? { questions: [] })
        setError(err.response?.data?.detail || 'Failed to load this quiz')
      } finally {
        setLoadingDetail(false)
      }
    }
  }

  // Countdown: resumes from the server-recorded start time, auto-submits at 0
  useEffect(() => {
    if (!detail || result || !detail.time_limit || !detail.started_at) {
      setSecondsLeft(null)
      return
    }
    const expiresAt = new Date(detail.started_at).getTime() + detail.time_limit * 60 * 1000
    const iv = setInterval(() => {
      const remaining = Math.max(0, Math.ceil((expiresAt - Date.now()) / 1000))
      setSecondsLeft(remaining)
      if (remaining <= 0) {
        clearInterval(iv)
        if (!autoSubmittedRef.current) {
          autoSubmittedRef.current = true
          handleSubmit(true)
        }
      }
    }, 1000)
    return () => clearInterval(iv)
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [detail, result])

  const selectAnswer = (questionId, index) => {
    setAnswers((prev) => ({ ...prev, [questionId]: index }))
  }

  const handleSubmit = async (timedOut = false) => {
    if (!detail || submitting) return
    setError('')
    const questions = detail.questions || []
    const unanswered = questions.filter((q) => answersRef.current[q.id] === undefined)
    if (!timedOut && unanswered.length > 0) {
      setError(`Please answer all ${questions.length} questions before submitting.`)
      return
    }
    setSubmitting(true)
    try {
      // timed-out auto-submit omits unanswered questions (graded as wrong)
      const payload = questions
        .filter((q) => answersRef.current[q.id] !== undefined)
        .map((q) => ({
          question_id: q.id,
          selected_index: answersRef.current[q.id],
        }))
      const res = await quizzesAPI.submit(quiz.id, payload, timedOut)
      setResult(res.data)
      setExpanded(false)
      setTimeout(() => setExpanded(true), 100)
    } catch (err) {
      setError(err.response?.data?.detail || 'Failed to submit quiz')
    } finally {
      setSubmitting(false)
    }
  }

  const scorePercent = result && result.total > 0
    ? Math.round((result.score / result.total) * 100)
    : 0
  const scoreTone = scorePercent >= 70 ? 'text-emerald-600' : scorePercent >= 40 ? 'text-amber-600' : 'text-red-500'

  const isExpired = quiz.deadline && new Date() > new Date(quiz.deadline)
  const deadlineFormatted = quiz.deadline
    ? new Date(quiz.deadline).toLocaleString('en-US', { dateStyle: 'medium', timeStyle: 'short' })
    : null
  const perStudent = quiz.total_questions || quiz.question_count

  return (
    <div className={`border rounded-xl bg-white overflow-hidden transition-all ${expanded ? 'border-accent-300 shadow-elevated' : 'border-surface-200'}`}>
      <button
        onClick={toggle}
        className="w-full flex items-start gap-3.5 p-4 sm:p-5 text-left hover:bg-surface-50/60 transition-colors"
      >
        <span className="w-10 h-10 rounded-xl bg-navy-950 text-accent-400 flex items-center justify-center shrink-0">
          <HelpCircle className="w-5 h-5" />
        </span>
        <div className="min-w-0 flex-1">
          <div className="flex items-center gap-2 flex-wrap">
            <h3 className="text-sm font-bold text-navy-900">{quiz.title}</h3>
            {result ? (
              <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full border text-2xs font-bold bg-emerald-50 text-emerald-700 border-emerald-200">
                Completed
              </span>
            ) : isExpired ? (
              <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full bg-red-50 text-red-600 border border-red-200 text-2xs font-bold">
                Expired
              </span>
            ) : (
              <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full bg-emerald-50 text-emerald-700 border border-emerald-200 text-2xs font-bold">
                Open
              </span>
            )}
          </div>
          <div className="flex flex-wrap items-center gap-x-4 gap-y-1 mt-1.5">
            {quiz.course_code && (
              <span className="inline-flex items-center gap-1 text-2xs text-navy-400">
                <BookOpen className="w-3 h-3 text-navy-300" />
                {quiz.course_code}
              </span>
            )}
            <span className="inline-flex items-center gap-1 text-2xs text-navy-400">
              <FileQuestion className="w-3 h-3 text-navy-300" />
              {perStudent} question{perStudent === 1 ? '' : 's'}
            </span>
            {(quiz.total_questions || 0) < (quiz.question_count || 0) && (
              <span className="inline-flex items-center gap-1 text-2xs text-sky-600 font-semibold">
                shuffled from {quiz.question_count}
              </span>
            )}
            {quiz.time_limit != null && quiz.time_limit > 0 && (
              <span className="inline-flex items-center gap-1 text-2xs text-navy-400">
                {quiz.time_limit} min
              </span>
            )}
            {deadlineFormatted && (
              <span className={`inline-flex items-center gap-1 text-2xs font-semibold ${isExpired ? 'text-red-500' : 'text-navy-400'}`}>
                {isExpired ? 'Deadline passed' : `Due: ${deadlineFormatted}`}
              </span>
            )}
            {result && (
              <span className={`inline-flex items-center gap-1 text-2xs font-bold ${scoreTone}`}>
                Score: {result.score}/{result.total}
              </span>
            )}
          </div>
        </div>
        <ChevronDown className={`w-4 h-4 text-navy-300 shrink-0 transition-transform ${expanded ? 'rotate-180' : ''}`} />
      </button>

      {expanded && (
        <div className="border-t border-surface-100 p-4 sm:p-5 space-y-4">
          {quiz.description && (
            <p className="text-sm text-navy-700 leading-relaxed whitespace-pre-wrap">{quiz.description}</p>
          )}

          {loadingDetail ? (
            <div className="flex items-center justify-center py-8">
              <div className="w-8 h-8 border-2 border-surface-200 border-t-accent-500 rounded-full animate-spin" />
            </div>
          ) : result ? (
            /* ── Result View ── */
            <div className="space-y-4">
              <div className={`flex items-center gap-4 p-4 rounded-xl border ${
                scorePercent >= 70
                  ? 'bg-emerald-50 border-emerald-200'
                  : scorePercent >= 40
                    ? 'bg-amber-50 border-amber-200'
                    : 'bg-red-50 border-red-200'
              }`}>
                <div className={`w-14 h-14 rounded-2xl flex items-center justify-center text-xl font-extrabold text-white shrink-0 ${
                  scorePercent >= 70 ? 'bg-emerald-500' : scorePercent >= 40 ? 'bg-amber-500' : 'bg-red-500'
                }`}>
                  {result.score}/{result.total}
                </div>
                <div>
                  <p className={`text-sm font-bold ${scoreTone}`}>
                    {scorePercent >= 70 ? 'Great job!' : scorePercent >= 40 ? 'Keep practicing!' : 'Needs improvement'}
                  </p>
                  <p className="text-xs text-navy-500 mt-0.5">
                    You scored {scorePercent}% — {result.score} out of {result.total} correct
                  </p>
                </div>
              </div>

              {(result.answers || []).map((a, i) => (
                <div
                  key={a.question_id}
                  className={`rounded-xl border p-4 ${
                    a.is_correct ? 'border-emerald-200 bg-emerald-50/50' : 'border-red-200 bg-red-50/50'
                  }`}
                >
                  <div className="flex items-start gap-2.5">
                    <span className={`w-6 h-6 rounded-full flex items-center justify-center shrink-0 mt-0.5 text-white ${
                      a.is_correct ? 'bg-emerald-500' : 'bg-red-500'
                    }`}>
                      {a.is_correct ? <CheckCircle2 className="w-3.5 h-3.5" /> : <X className="w-3.5 h-3.5" />}
                    </span>
                    <div className="flex-1 min-w-0">
                      <p className="text-sm font-semibold text-navy-900">
                        <span className="text-navy-400 font-bold mr-1.5">Q{i + 1}.</span>
                        {a.question_text}
                      </p>
                      <div className="mt-2.5 space-y-1.5">
                        {a.options.map((opt, oi) => {
                          const isCorrect = oi === a.correct_index
                          const isSelected = oi === a.selected_index
                          return (
                            <div key={oi} className={`flex items-center gap-2.5 text-xs rounded-lg px-2.5 py-1.5 ${
                              isCorrect ? 'bg-emerald-100 text-emerald-800 font-semibold' :
                              isSelected && !isCorrect ? 'bg-red-100 text-red-700 line-through' :
                              'text-navy-500'
                            }`}>
                              <span className={`w-5 h-5 shrink-0 rounded-full border-2 flex items-center justify-center text-[10px] font-bold ${
                                isCorrect ? 'border-emerald-500 bg-emerald-500 text-white' :
                                isSelected ? 'border-red-500 bg-red-500 text-white' :
                                'border-surface-300 text-navy-400'
                              }`}>
                                {String.fromCharCode(65 + oi)}
                              </span>
                              <span>{opt}</span>
                              {isCorrect && <span className="ml-auto text-emerald-600 font-bold">✓ Correct</span>}
                              {isSelected && !isCorrect && <span className="ml-auto text-red-500 font-bold">✗ Your answer</span>}
                            </div>
                          )
                        })}
                      </div>
                    </div>
                  </div>
                </div>
              ))}
            </div>
          ) : (
            /* ── Quiz Form View ── */
            <div className="space-y-4">
              {error && (
                <div className="flex items-start gap-2 bg-red-50 text-red-700 px-3.5 py-2.5 rounded-xl text-xs font-medium border border-red-200">
                  <AlertTriangle className="w-4 h-4 mt-0.5 shrink-0" />
                  {error}
                </div>
              )}

              {secondsLeft != null && (
                <div
                  className={`flex items-center gap-2 px-4 py-3 rounded-xl border text-xs font-bold ${
                    secondsLeft <= 60
                      ? 'bg-red-50 border-red-200 text-red-600'
                      : 'bg-navy-950 border-navy-950 text-accent-400'
                  }`}
                >
                  <Timer className={`w-4 h-4 shrink-0 ${secondsLeft <= 60 ? 'animate-pulse' : ''}`} />
                  {secondsLeft > 0
                    ? `Time remaining: ${Math.floor(secondsLeft / 60)}:${String(secondsLeft % 60).padStart(2, '0')}`
                    : "Time's up — submitting..."}
                </div>
              )}

              {(detail?.questions?.length > 0) ? (
                <>
                  <div className="flex items-center gap-2 text-xs text-navy-500 bg-sky-50 border border-sky-200 rounded-xl px-3.5 py-2.5">
                    <Shuffle className="w-3.5 h-3.5 text-sky-600 shrink-0" />
                    These {detail.questions.length} questions were shuffled for you — another student may see different ones.
                  </div>

                  {detail.questions.map((q, i) => (
                    <div key={q.id} className="rounded-xl border border-surface-100 bg-surface-50/70 p-4">
                      <p className="text-sm font-semibold text-navy-900">
                        <span className="text-navy-400 font-bold mr-1.5">Q{i + 1}.</span>
                        {q.text}
                      </p>
                      <div className="mt-3 space-y-2">
                        {q.options.map((opt, oi) => (
                          <button
                            key={oi}
                            type="button"
                            onClick={() => selectAnswer(q.id, oi)}
                            className={`w-full flex items-center gap-2.5 text-left text-xs rounded-lg px-3 py-2.5 border transition-all ${
                              answers[q.id] === oi
                                ? 'border-accent-400 bg-accent-50 text-navy-900 font-semibold shadow-sm'
                                : 'border-surface-200 bg-white text-navy-600 hover:border-accent-200 hover:bg-surface-50'
                            }`}
                          >
                            <span className={`w-5 h-5 shrink-0 rounded-full border-2 flex items-center justify-center font-bold text-[10px] transition-colors ${
                              answers[q.id] === oi
                                ? 'border-accent-500 bg-accent-500 text-white'
                                : 'border-surface-300 text-navy-400'
                            }`}>
                              {String.fromCharCode(65 + oi)}
                            </span>
                            <span>{opt}</span>
                          </button>
                        ))}
                      </div>
                    </div>
                  ))}

                  {isExpired && (
                    <div className="flex items-center gap-2 bg-red-50 border border-red-200 text-red-600 px-4 py-3 rounded-xl text-xs font-semibold">
                      The deadline for this quiz has passed. You can no longer submit answers.
                    </div>
                  )}

                  {!isExpired && (
                    <div className="flex items-center justify-between pt-2">
                      <p className="text-xs text-navy-400">
                        {Object.keys(answers).length} of {detail.questions.length} answered
                      </p>
                      <button
                        onClick={handleSubmit}
                        disabled={submitting}
                        className="inline-flex items-center gap-2 px-5 py-2.5 rounded-xl text-sm font-bold bg-accent-500 text-navy-950 hover:bg-accent-400 disabled:opacity-50 disabled:cursor-not-allowed transition-all shadow-md"
                      >
                        {submitting ? (
                          <>
                            <span className="w-4 h-4 border-2 border-navy-950/30 border-t-navy-950 rounded-full animate-spin" />
                            Submitting...
                          </>
                        ) : (
                          <>
                            Submit Quiz
                          </>
                        )}
                      </button>
                    </div>
                  )}
                </>
              ) : (
                <p className="text-sm text-navy-400 text-center py-4">No questions available for this quiz.</p>
              )}
            </div>
          )}
        </div>
      )}
    </div>
  )
}
