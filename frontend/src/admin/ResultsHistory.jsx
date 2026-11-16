import { useEffect, useState, useCallback } from 'react'
import { ArrowLeft, BookOpen, ChevronRight, Download, GraduationCap, Users } from 'lucide-react'
import { historyAPI } from '../services/api'

const SHIFTS = [
  { value: 'morning', label: 'Morning' },
  { value: 'evening', label: 'Evening' },
]

const groupKey = (g) => `${g.session}-${g.semester}-${g.session_type}`

// Saves an Excel blob using the server's filename (falls back to a local name)
function saveBlob(response, fallbackName) {
  const m = /filename="([^"]+)"/.exec(response.headers?.['content-disposition'] || '')
  const url = URL.createObjectURL(response.data)
  const a = document.createElement('a')
  a.href = url
  a.download = m ? m[1] : fallbackName
  document.body.appendChild(a)
  a.click()
  a.remove()
  URL.revokeObjectURL(url)
}

export default function ResultsHistory() {
  const [groups, setGroups] = useState([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const [busy, setBusy] = useState('') // key of the download in progress
  const [shift, setShift] = useState('morning')
  const [openKey, setOpenKey] = useState(null) // semester card opened to show its subjects

  const load = useCallback(async () => {
    setLoading(true)
    setError('')
    try {
      const res = await historyAPI.listCourses()
      setGroups(res.data)
    } catch (err) {
      setError(err.response?.data?.detail || 'Could not load results history')
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => { load() }, [load])

  const download = async (key, request, fallbackName) => {
    setBusy(key)
    setError('')
    try {
      saveBlob(await request(), fallbackName)
    } catch {
      setError('Download failed. Please try again.')
    } finally {
      setBusy('')
    }
  }

  const switchShift = (value) => {
    setShift(value)
    setOpenKey(null)
  }

  const visibleGroups = groups.filter((g) => g.session_type === shift)
  const openGroup = visibleGroups.find((g) => groupKey(g) === openKey) || null

  return (
    <div className="p-5 lg:p-8 max-w-7xl mx-auto w-full">
      {/* Header — same pattern as the Promotion page */}
      <div className="mb-8 text-center">
        <span className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full bg-accent-500/10 border border-accent-500/20 text-accent-600 text-[11px] font-semibold mb-3">
          <GraduationCap className="w-3 h-3" />
          Results History
        </span>
        <h1 className="text-3xl font-bold text-navy-900 tracking-tight">History</h1>
        <p className="text-sm text-navy-400 mt-1">
          Quiz results for every subject, grouped by semester. Promoted classes stay here after their courses leave the teacher view.
        </p>
      </div>

      {/* Shift switcher */}
      <div className="flex justify-center gap-2 mb-6">
        <div className="inline-flex gap-1 p-1 bg-surface-100 rounded-lg">
          {SHIFTS.map((s) => (
            <button
              key={s.value}
              type="button"
              onClick={() => switchShift(s.value)}
              className={`px-5 py-1.5 rounded-md text-xs font-semibold transition-all whitespace-nowrap ${
                shift === s.value
                  ? 'bg-gradient-to-r from-amber-400 to-amber-500 text-navy-900 shadow-sm shadow-amber-400/20'
                  : 'text-navy-400 hover:text-navy-600'
              }`}
            >
              {s.label}
            </button>
          ))}
        </div>
      </div>

      {error && (
        <div className="mb-6 text-sm text-red-600 bg-red-50 border border-red-200 rounded-xl px-4 py-3">{error}</div>
      )}

      {loading && <div className="text-center py-16 text-navy-400 text-sm">Loading history...</div>}

      {/* ── Level 2: subjects of one semester, one card per subject ── */}
      {!loading && openGroup && (
        <>
          <div className="flex flex-wrap items-center justify-between gap-3 mb-6">
            <button
              type="button"
              onClick={() => setOpenKey(null)}
              className="inline-flex items-center gap-1.5 text-xs font-semibold text-navy-500 hover:text-navy-900 transition-colors"
            >
              <ArrowLeft className="w-3.5 h-3.5" />
              Back to semesters
            </button>
            <button
              type="button"
              disabled={busy === `group-${groupKey(openGroup)}`}
              onClick={() => download(
                `group-${groupKey(openGroup)}`,
                () => historyAPI.exportGroup(openGroup.session, openGroup.semester, openGroup.session_type),
                `Results_S${openGroup.semester}_${openGroup.session}_${openGroup.session_type}.xlsx`,
              )}
              className="inline-flex items-center gap-2 px-4 py-2 rounded-xl bg-gradient-to-r from-amber-400 to-amber-500 text-navy-900 text-xs font-semibold shadow-sm shadow-amber-400/20 hover:from-amber-300 hover:to-amber-400 disabled:opacity-60 transition-all"
            >
              <Download className="w-3.5 h-3.5" />
              {busy === `group-${groupKey(openGroup)}` ? 'Preparing...' : 'Download all subjects (Excel)'}
            </button>
          </div>

          <div className="mb-5">
            <p className="text-xs font-semibold text-navy-400 uppercase tracking-wider mb-1">
              Session {openGroup.session} · {SHIFTS.find((s) => s.value === openGroup.session_type)?.label}
            </p>
            <p className="text-2xl font-extrabold text-navy-900">Semester {openGroup.semester}</p>
          </div>

          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
            {openGroup.courses.map((c) => (
              <div
                key={c.id}
                className="border border-surface-200 rounded-2xl p-6 bg-white flex flex-col hover:border-accent-300 hover:shadow-elevated transition-all duration-200"
              >
                <div className="flex items-start justify-between gap-3 mb-3">
                  <div className="min-w-0">
                    <p className="text-xs font-semibold text-navy-400 uppercase tracking-wider mb-1">{c.course_code}</p>
                    <p className="text-base font-bold text-navy-900 truncate">{c.title}</p>
                  </div>
                  <span className={`text-[11px] font-semibold px-2 py-0.5 rounded-full border shrink-0 ${
                    c.is_active
                      ? 'bg-emerald-50 text-emerald-700 border-emerald-200'
                      : 'bg-surface-100 text-navy-500 border-surface-200'
                  }`}>
                    {c.is_active ? 'Active' : 'Archived'}
                  </span>
                </div>
                <div className="flex items-center gap-4 text-xs text-navy-400 mb-5">
                  <span className="inline-flex items-center gap-1.5">
                    <Users className="w-3.5 h-3.5" />
                    {c.teacher_name || 'No teacher'}
                  </span>
                  <span className="inline-flex items-center gap-1.5">
                    <BookOpen className="w-3.5 h-3.5" />
                    {c.quiz_count} quiz{c.quiz_count === 1 ? '' : 'zes'}
                  </span>
                </div>
                <button
                  type="button"
                  disabled={busy === `course-${c.id}`}
                  onClick={() => download(
                    `course-${c.id}`,
                    () => historyAPI.exportCourse(c.id),
                    `${c.course_code}_results.xlsx`,
                  )}
                  className="mt-auto w-full inline-flex items-center justify-center gap-2 px-4 py-2.5 rounded-xl border border-surface-200 text-xs font-semibold text-navy-700 hover:bg-surface-50 hover:border-accent-300 disabled:opacity-60 transition-colors"
                >
                  <Download className="w-3.5 h-3.5" />
                  {busy === `course-${c.id}` ? 'Preparing...' : 'Download Excel'}
                </button>
              </div>
            ))}
          </div>
        </>
      )}

      {/* ── Level 1: semester cards (same size as the Promotion session cards) ── */}
      {!loading && !openGroup && visibleGroups.length === 0 && (
        <div className="text-center py-16 text-sm text-navy-400 bg-white border border-surface-200 rounded-2xl">
          No {shift} shift classes yet. Results will appear here once courses are created.
        </div>
      )}

      {!loading && !openGroup && visibleGroups.length > 0 && (
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
          {visibleGroups.map((g) => (
            <button
              key={groupKey(g)}
              type="button"
              onClick={() => setOpenKey(groupKey(g))}
              className="group text-left border border-surface-200 rounded-2xl p-6 bg-white hover:border-accent-300 hover:shadow-elevated transition-all duration-200"
            >
              <div className="flex items-start justify-between mb-4">
                <div>
                  <p className="text-xs font-semibold text-navy-400 uppercase tracking-wider mb-1">Session {g.session}</p>
                  <p className="text-2xl font-extrabold text-navy-900">Semester {g.semester}</p>
                </div>
                <div className="w-10 h-10 rounded-xl bg-accent-50 flex items-center justify-center group-hover:bg-accent-100 transition-colors">
                  <GraduationCap className="w-5 h-5 text-accent-500" />
                </div>
              </div>
              <div className="flex items-center gap-2">
                <BookOpen className="w-4 h-4 text-navy-400" />
                <span className="text-sm font-semibold text-navy-700">{g.courses.length}</span>
                <span className="text-xs text-navy-400">subject{g.courses.length === 1 ? '' : 's'}</span>
              </div>
              <div className="flex items-center justify-between mt-4 pt-4 border-t border-surface-100">
                <span className="text-xs text-navy-400">Click to view subjects</span>
                <ChevronRight className="w-4 h-4 text-navy-300 group-hover:text-accent-500 transition-colors" />
              </div>
            </button>
          ))}
        </div>
      )}
    </div>
  )
}
