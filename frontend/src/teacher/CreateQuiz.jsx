import { useState, useEffect, useRef } from 'react'
import { useNavigate, Link } from 'react-router-dom'
import { coursesAPI, quizzesAPI } from '../services/api'
import Button from '../components/Button'
import {
  BookOpen, FileText, AlertCircle,
  Plus, Trash2, CheckCircle2, UploadCloud, FileSpreadsheet,
  Shuffle, X, Loader2, ClipboardList, ChevronLeft, ChevronRight,
} from 'lucide-react'

export default function CreateQuiz({ courseId, onSuccess, onCancel }) {
  const [courses, setCourses] = useState([])
  const [form, setForm] = useState({
    course_id: '', title: '', description: '', time_limit: '', deadline: '', total_questions: '',
  })
  const [mode, setMode] = useState('manual') // 'file' | 'manual'

  // File mode state
  const [file, setFile] = useState(null)
  const [parsed, setParsed] = useState(null) // { questions: [], count }
  const [parsing, setParsing] = useState(false)
  const [parseError, setParseError] = useState('')
  const fileInputRef = useRef(null)
  const [dragOver, setDragOver] = useState(false)

  // Manual mode state
  const [questions, setQuestions] = useState([
    { text: '', options: ['', '', '', ''], correct: 0 },
  ])

  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')
  const [success, setSuccess] = useState('')
  const navigate = useNavigate()

  useEffect(() => {
    coursesAPI.list()
      .then((r) => {
        setCourses(r.data)
        if (courseId) {
          setForm((f) => ({ ...f, course_id: f.course_id || courseId }))
        } else if (r.data.length > 0) {
          setForm((f) => ({ ...f, course_id: f.course_id || r.data[0].id }))
        }
      })
      .catch(console.error)
  }, [courseId])

  // ── File upload + preview parse ─────────────────────
  const handleFile = async (f) => {
    if (!f) return
    setError('')
    setParseError('')
    setParsed(null)
    setFile(f)
    setParsing(true)
    try {
      const r = await quizzesAPI.parseFile(f)
      setParsed(r.data)
    } catch (err) {
      setParseError(err.response?.data?.detail || 'Could not parse this file')
      setFile(null)
    } finally {
      setParsing(false)
    }
  }

  const onDrop = (e) => {
    e.preventDefault()
    setDragOver(false)
    handleFile(e.dataTransfer.files?.[0])
  }

  const clearFile = () => {
    setFile(null)
    setParsed(null)
    setParseError('')
    if (fileInputRef.current) fileInputRef.current.value = ''
  }

  // ── Question helpers (manual mode) ──────────────────
  const addQuestion = () => setQuestions([...questions, { text: '', options: ['', '', '', ''], correct: 0 }])

  const removeQuestion = (idx) => {
    if (questions.length <= 1) return
    setQuestions(questions.filter((_, i) => i !== idx))
  }

  const updateQuestion = (idx, field, value) => {
    const updated = [...questions]
    updated[idx] = { ...updated[idx], [field]: value }
    setQuestions(updated)
  }

  const updateOption = (qIdx, oIdx, value) => {
    const updated = [...questions]
    updated[qIdx].options[oIdx] = value
    setQuestions(updated)
  }

  // ── Submit ──────────────────────────────────────────
  const handleSubmit = async (e) => {
    e.preventDefault()
    setError('')
    setSuccess('')

    if (!form.course_id) {
      setError('Select a course first. Admin must create one from Manage Courses.')
      return
    }
    if (mode === 'file' && !file) {
      setError('Upload a question-bank file (DOCX, CSV or XLSX).')
      return
    }

    let validManual = []
    if (mode === 'manual') {
      for (let i = 0; i < questions.length; i++) {
        const q = questions[i]
        const filledOptions = q.options.filter((o) => o.trim())
        if (!q.text.trim() && filledOptions.length < 2) continue
        if (!q.text.trim()) {
          setError(`Question ${i + 1} text is required`)
          return
        }
        if (filledOptions.length < 2) {
          setError(`Question ${i + 1} needs at least 2 options`)
          return
        }
        if (q.correct >= filledOptions.length) {
          setError(`Question ${i + 1}: selected correct answer is empty. Pick a valid option.`)
          return
        }
      }
      validManual = questions.filter((q) => {
        const opts = q.options.filter((o) => o.trim())
        return q.text.trim() || opts.length >= 2
      }).map((q) => {
        const options = q.options.map((o) => o.trim()).filter((o) => o.length)
        const correct = Math.min(q.correct, options.length - 1)
        return { text: q.text.trim(), options, correct: correct < 0 ? 0 : correct }
      })
      if (validManual.length === 0 && !file) {
        setError('Add at least one question')
        return
      }
    }

    if (form.total_questions && parseInt(form.total_questions) < 1) {
      setError('Total questions must be at least 1')
      return
    }

    setLoading(true)
    try {
      const formData = new FormData()
      formData.append('course_id', form.course_id)
      formData.append('title', form.title.trim())
      if (form.description) formData.append('description', form.description.trim())
      if (form.time_limit) formData.append('time_limit', parseInt(form.time_limit))
      if (form.deadline) formData.append('deadline', new Date(form.deadline).toISOString())
      if (form.total_questions) formData.append('total_questions', parseInt(form.total_questions))
      if (mode === 'manual' && validManual.length > 0) {
        formData.append('questions', JSON.stringify(validManual))
      }
      if (mode === 'file' && file) {
        formData.append('question_file', file)
      }

      await quizzesAPI.create(formData)
      setSuccess('Quiz created successfully! Students can now attempt it.')
      if (onSuccess) setTimeout(() => onSuccess(), 900)
      else setTimeout(() => navigate('/teacher/quizzes'), 1200)
    } catch (err) {
      setError(err.response?.data?.detail || 'Failed to create quiz')
    } finally {
      setLoading(false)
    }
  }

  const bankSize = mode === 'file' ? (parsed?.count || 0) : questions.filter((q) => q.text.trim()).length
  const maxTotal = mode === 'file' ? (parsed?.count || 0) : null

  const selectedCourse = courses.find((c) => c.id === form.course_id)

  return (
    <div className={`max-w-3xl mx-auto ${courseId ? '' : 'p-5 lg:p-8'}`}>
      {!courseId && (
        <>
      {/* Header */}
      <div className="text-center mb-6">
        <span className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full bg-accent-500/10 border border-accent-500/20 text-accent-600 text-[11px] font-semibold mb-3">
          <ClipboardList className="w-3 h-3" />
          New Quiz
        </span>
        <h1 className="text-3xl font-extrabold text-navy-900 tracking-tight">Create Quiz</h1>
        <p className="text-navy-400 mt-1.5">Build a quiz for one of your courses — manual questions or a question-bank file.</p>
      </div>

      {/* Breadcrumbs */}
      <div className="flex items-center gap-2 mb-5 text-xs flex-wrap">
        <Link to="/teacher/quizzes" className="inline-flex items-center gap-1 font-semibold text-navy-500 hover:text-accent-600 transition-colors">
          <ChevronLeft className="w-3.5 h-3.5" />
          Quizzes
        </Link>
        <ChevronRight className="w-3 h-3 text-navy-300" />
        <span className="inline-flex items-center gap-1 font-semibold text-navy-800">
          <Plus className="w-3.5 h-3.5" />
          New Quiz
        </span>
      </div>
        </>
      )}

      {error && (
        <div className="flex items-start gap-3 bg-danger-light text-danger-dark px-4 py-3 rounded-xl mb-6 text-sm font-medium border border-danger/20">
          <AlertCircle className="w-4 h-4 mt-0.5 shrink-0" />
          <span>{typeof error === 'string' ? error : JSON.stringify(error)}</span>
        </div>
      )}

      {success && (
        <div className="flex items-start gap-3 bg-success-light text-success-dark px-4 py-3 rounded-xl mb-6 text-sm font-medium">
          <CheckCircle2 className="w-4 h-4 mt-0.5 shrink-0" />
          {success}
        </div>
      )}

      <form onSubmit={handleSubmit} className="space-y-5">
        {/* ── Basic Info ─────────────────────────── */}
        <div className="border border-surface-200 rounded-xl bg-white p-6 lg:p-8 space-y-5">
          <div>
            <label className="input-label">Course</label>
            <div className="relative">
              <BookOpen className="w-4 h-4 text-navy-300 absolute left-3 top-1/2 -translate-y-1/2 pointer-events-none" />
              {courseId ? (
                <input
                  type="text"
                  readOnly
                  value={selectedCourse ? `${selectedCourse.course_code} — ${selectedCourse.title}` : ''}
                  className="input-field pl-10 bg-surface-50 text-navy-700 cursor-default"
                />
              ) : (
                <select
                  value={form.course_id}
                  onChange={(e) => setForm({ ...form, course_id: e.target.value })}
                  className="input-field pl-10"
                  required
                >
                  <option value="">
                    {courses.length === 0 ? 'No courses yet — ask admin to create one' : 'Select a course…'}
                  </option>
                  {courses.map((c) => (
                    <option key={c.id} value={c.id}>{c.course_code} — {c.title}</option>
                  ))}
                </select>
              )}
            </div>
          </div>

          <div>
            <label className="input-label">Quiz Title</label>
            <div className="relative">
              <FileText className="w-4 h-4 text-navy-300 absolute left-3 top-1/2 -translate-y-1/2 pointer-events-none" />
              <input value={form.title} onChange={(e) => setForm({ ...form, title: e.target.value })}
                className="input-field pl-10" placeholder="e.g. Quiz 1: Data Types" required />
            </div>
          </div>

          <div>
            <label className="input-label">Description (optional)</label>
            <textarea value={form.description} rows={3} onChange={(e) => setForm({ ...form, description: e.target.value })}
              className="input-field resize-none" placeholder="Any instructions for students..." />
          </div>

          <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
            <div>
              <label className="input-label min-h-8">Time Limit (minutes, optional)</label>
              <input type="number" value={form.time_limit} min={1}
                onChange={(e) => setForm({ ...form, time_limit: e.target.value })}
                className="input-field" placeholder="No limit" />
            </div>
            <div>
              <label className="input-label min-h-8">Deadline (optional)</label>
              <input type="datetime-local" value={form.deadline}
                onChange={(e) => setForm({ ...form, deadline: e.target.value })}
                className="input-field" />
            </div>
            <div>
              <label className="input-label min-h-8">No of MCQs sent per user</label>
              <input type="number" value={form.total_questions} min={1} max={maxTotal || undefined}
                onChange={(e) => setForm({ ...form, total_questions: e.target.value })}
                className="input-field"
                placeholder={mode === 'file' ? (parsed ? `All ${parsed.count}` : 'All') : 'All'} />
              <p className="mt-1 text-[10px] text-navy-400 flex items-center gap-1">
                <Shuffle className="w-3 h-3 shrink-0" />
                {bankSize > 0
                  ? `Bank: ${bankSize} — leave empty to send all, or set a number for a shuffled subset`
                  : 'Each student gets a shuffled subset of this size'}
              </p>
            </div>
          </div>
        </div>

        {/* ── Question source toggle ─────────────── */}
        <div className="border border-surface-200 rounded-xl bg-white p-6 lg:p-8 space-y-5">
          <div className="flex items-center justify-between gap-3 flex-wrap">
            <label className="input-label !mb-0">Questions</label>
            <div className="flex items-center gap-3 flex-wrap">
              <span className="text-xs text-navy-400">
                {mode === 'file'
                  ? `${parsed?.count || 0} parsed`
                  : `${questions.length} question${questions.length !== 1 ? 's' : ''}`}
              </span>
              <div className="flex rounded-lg border border-surface-200 p-0.5 bg-surface-50">
                <button
                  type="button"
                  onClick={() => setMode('file')}
                  className={`px-3 py-1.5 text-xs font-semibold rounded-md transition-colors flex items-center gap-1.5 ${
                    mode === 'file' ? 'bg-accent-500 text-navy-950 shadow-sm' : 'text-navy-500 hover:text-navy-800'
                  }`}
                >
                  <UploadCloud className="w-3.5 h-3.5" />
                  Upload file
                </button>
                <button
                  type="button"
                  onClick={() => setMode('manual')}
                  className={`px-3 py-1.5 text-xs font-semibold rounded-md transition-colors flex items-center gap-1.5 ${
                    mode === 'manual' ? 'bg-accent-500 text-navy-950 shadow-sm' : 'text-navy-500 hover:text-navy-800'
                  }`}
                >
                  <Plus className="w-3.5 h-3.5" />
                  Write manually
                </button>
              </div>
            </div>
          </div>

          {/* ── File mode ── */}
          {mode === 'file' && (
            <div className="space-y-4">
              {!file ? (
                <div
                  onDragOver={(e) => { e.preventDefault(); setDragOver(true) }}
                  onDragLeave={() => setDragOver(false)}
                  onDrop={onDrop}
                  onClick={() => fileInputRef.current?.click()}
                  className={`relative border-2 border-dashed rounded-xl p-10 text-center cursor-pointer transition-all ${
                    dragOver
                      ? 'border-accent-400 bg-accent-500/5'
                      : 'border-surface-300 hover:border-accent-300 bg-surface-50/60 hover:bg-accent-500/5'
                  }`}
                >
                  <input
                    ref={fileInputRef}
                    type="file"
                    accept=".docx,.csv,.xlsx"
                    className="hidden"
                    onChange={(e) => handleFile(e.target.files?.[0])}
                  />
                  {parsing ? (
                    <div className="flex flex-col items-center gap-3">
                      <Loader2 className="w-8 h-8 text-accent-500 animate-spin" />
                      <p className="text-sm font-semibold text-navy-600">Parsing your question bank…</p>
                    </div>
                  ) : (
                    <>
                      <span className="inline-flex w-12 h-12 rounded-2xl bg-accent-500/10 border border-accent-200 items-center justify-center mb-3">
                        <FileSpreadsheet className="w-6 h-6 text-accent-600" />
                      </span>
                      <p className="text-sm font-bold text-navy-800">
                        Drop your question bank here, or click to browse
                      </p>
                      <p className="text-xs text-navy-400 mt-1">
                        Supports <span className="font-semibold text-navy-600">.docx</span>,{' '}
                        <span className="font-semibold text-navy-600">.csv</span> and{' '}
                        <span className="font-semibold text-navy-600">.xlsx</span>
                      </p>
                      <p className="text-[10px] text-navy-400 mt-3 leading-relaxed max-w-md mx-auto">
                        CSV/XLSX columns: Question, Option1…Option4, Answer — or numbered DOCX questions
                        with a)-d) options and an "Answer:" line.
                      </p>
                    </>
                  )}
                </div>
              ) : (
                <div className="rounded-xl border border-surface-200 overflow-hidden">
                  <div className="flex items-center justify-between gap-3 px-4 py-3 bg-surface-50 border-b border-surface-200">
                    <div className="flex items-center gap-2 min-w-0">
                      <FileSpreadsheet className="w-4 h-4 text-accent-600 shrink-0" />
                      <span className="text-xs font-semibold text-navy-800 truncate">{file.name}</span>
                      {parsed && (
                        <span className="px-2 py-0.5 rounded-full bg-emerald-50 text-emerald-700 border border-emerald-200 text-2xs font-bold shrink-0">
                          {parsed.count} questions parsed
                        </span>
                      )}
                    </div>
                    <button type="button" onClick={clearFile}
                      className="w-7 h-7 rounded-lg flex items-center justify-center text-navy-400 hover:text-danger hover:bg-danger-light transition-colors shrink-0">
                      <X className="w-4 h-4" />
                    </button>
                  </div>

                  {parsed && (
                    <div className="max-h-64 overflow-y-auto divide-y divide-surface-100">
                      {parsed.questions.slice(0, 50).map((q, i) => (
                        <div key={i} className="px-4 py-3">
                          <p className="text-xs font-semibold text-navy-800">
                            <span className="text-navy-400 mr-1.5">{i + 1}.</span>
                            {q.text}
                          </p>
                          <div className="flex flex-wrap gap-1.5 mt-1.5">
                            {q.options.map((opt, oi) => (
                              <span key={oi} className={`px-2 py-0.5 rounded text-[10px] font-medium ${
                                oi === q.correct
                                  ? 'bg-emerald-100 text-emerald-800 font-bold'
                                  : 'bg-surface-100 text-navy-500'
                              }`}>
                                {String.fromCharCode(65 + oi)}. {opt}
                              </span>
                            ))}
                          </div>
                        </div>
                      ))}
                      {parsed.questions.length > 50 && (
                        <p className="px-4 py-2.5 text-[10px] text-navy-400 text-center">
                          …and {parsed.questions.length - 50} more
                        </p>
                      )}
                    </div>
                  )}
                </div>
              )}

              {parseError && (
                <div className="flex items-start gap-2 bg-danger-light text-danger-dark px-3.5 py-2.5 rounded-xl text-xs font-medium">
                  <AlertCircle className="w-3.5 h-3.5 mt-0.5 shrink-0" />
                  {parseError}
                </div>
              )}
            </div>
          )}

          {/* ── Manual mode ── */}
          {mode === 'manual' && (
            <div className="space-y-5">
              {questions.map((q, qIdx) => (
                <div key={qIdx} className="border border-surface-200 rounded-xl p-5 space-y-4 relative">
                  <div className="flex items-start justify-between gap-3">
                    <span className="inline-flex items-center justify-center w-7 h-7 rounded-lg bg-accent-500/10 text-accent-600 text-xs font-bold shrink-0 mt-0.5">
                      {qIdx + 1}
                    </span>
                    <div className="flex-1">
                      <input
                        value={q.text}
                        onChange={(e) => updateQuestion(qIdx, 'text', e.target.value)}
                        className="input-field"
                        placeholder={`Question ${qIdx + 1}`}
                      />
                    </div>
                    {questions.length > 1 && (
                      <button
                        type="button"
                        onClick={() => removeQuestion(qIdx)}
                        className="p-2 rounded-lg hover:bg-danger-light text-navy-300 hover:text-danger transition-colors shrink-0"
                      >
                        <Trash2 className="w-4 h-4" />
                      </button>
                    )}
                  </div>

                  <div className="grid grid-cols-1 sm:grid-cols-2 gap-3 pl-10">
                    {q.options.map((opt, oIdx) => (
                      <div key={oIdx} className="flex items-center gap-2">
                        <button
                          type="button"
                          onClick={() => updateQuestion(qIdx, 'correct', oIdx)}
                          className={`w-6 h-6 rounded-full border-2 flex items-center justify-center shrink-0 transition-colors ${
                            q.correct === oIdx
                              ? 'border-emerald-500 bg-emerald-500 text-white'
                              : 'border-surface-200 hover:border-accent-300'
                          }`}
                        >
                          {q.correct === oIdx && <CheckCircle2 className="w-3.5 h-3.5" />}
                        </button>
                        <input
                          value={opt}
                          onChange={(e) => updateOption(qIdx, oIdx, e.target.value)}
                          className="input-field text-sm"
                          placeholder={`Option ${oIdx + 1}`}
                        />
                      </div>
                    ))}
                  </div>
                  <p className="text-[10px] text-navy-400 pl-10">Click the circle to mark the correct answer.</p>
                </div>
              ))}

              <button
                type="button"
                onClick={addQuestion}
                className="w-full flex items-center justify-center gap-2 px-4 py-3 rounded-xl border-2 border-dashed border-surface-200 hover:border-accent-300 text-sm font-semibold text-navy-500 hover:text-accent-600 bg-surface-50 hover:bg-accent-500/5 transition-colors"
              >
                <Plus className="w-4 h-4" />
                Add Another Question
              </button>
            </div>
          )}
        </div>

        {/* ── Actions ────────────────────────────── */}
        <div className="flex flex-col sm:flex-row gap-3 justify-end pt-2">
          <Button variant="ghost" type="button" onClick={() => (onCancel ? onCancel() : navigate('/teacher/quizzes'))}>Cancel</Button>
          <Button type="submit" disabled={loading || (mode === 'file' && (!file || parsing))}>
            {loading ? 'Creating...' : 'Create Quiz'}
          </Button>
        </div>
      </form>
    </div>
  )
}
