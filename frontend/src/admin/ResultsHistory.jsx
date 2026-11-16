import { useEffect, useState, useCallback } from 'react'
import { BookOpen, Clock, Download } from 'lucide-react'
import { historyAPI } from '../services/api'

const shiftLabel = (s) => `${s.charAt(0).toUpperCase()}${s.slice(1)} shift`

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

  return (
    <div className="space-y-6">
      <div>
        <p className="text-xs font-semibold uppercase tracking-wider text-accent-600">Results</p>
        <h1 className="text-3xl font-bold text-navy-900 tracking-tight">History</h1>
        <p className="text-sm text-navy-400 mt-1">
          Quiz results for every subject, grouped by semester. Promoted classes stay here after their courses leave the teacher view.
        </p>
      </div>

      {error && (
        <div className="text-sm text-red-600 bg-red-50 border border-red-200 rounded-xl px-4 py-3">{error}</div>
      )}

      {loading ? (
        <p className="text-sm text-navy-400">Loading history...</p>
      ) : groups.length === 0 ? (
        <div className="text-center py-16 text-sm text-navy-400 bg-white border border-surface-200 rounded-xl">
          No courses yet. Results will appear here once courses are created.
        </div>
      ) : (
        groups.map((g) => {
          const key = `${g.session}-${g.semester}-${g.session_type}`
          return (
            <section key={key} className="bg-white border border-surface-200 rounded-xl overflow-hidden">
              <div className="flex flex-wrap items-center justify-between gap-3 p-4 sm:p-5 border-b border-surface-100">
                <div className="min-w-0">
                  <h2 className="text-base font-bold text-navy-900 flex items-center gap-2">
                    <Clock className="w-4 h-4 text-navy-400" />
                    Semester {g.semester}
                  </h2>
                  <p className="text-xs text-navy-400 mt-0.5">
                    Session {g.session} · {shiftLabel(g.session_type)} · {g.courses.length} subject{g.courses.length === 1 ? '' : 's'}
                  </p>
                </div>
                <button
                  type="button"
                  disabled={busy === `group-${key}`}
                  onClick={() => download(
                    `group-${key}`,
                    () => historyAPI.exportGroup(g.session, g.semester, g.session_type),
                    `Results_S${g.semester}_${g.session}_${g.session_type}.xlsx`,
                  )}
                  className="inline-flex items-center gap-2 px-3.5 py-2 rounded-lg bg-navy-950 text-white text-xs font-semibold hover:bg-navy-800 disabled:opacity-60"
                >
                  <Download className="w-3.5 h-3.5" />
                  {busy === `group-${key}` ? 'Preparing...' : 'Download all subjects (Excel)'}
                </button>
              </div>

              <ul className="divide-y divide-surface-100">
                {g.courses.map((c) => (
                  <li key={c.id} className="flex flex-wrap sm:flex-nowrap items-center gap-3 px-4 sm:px-5 py-3.5">
                    <span className="w-9 h-9 rounded-lg bg-surface-100 text-navy-500 flex items-center justify-center shrink-0">
                      <BookOpen className="w-4 h-4" />
                    </span>
                    <div className="min-w-0 flex-1">
                      <div className="flex items-center gap-2 flex-wrap">
                        <span className="text-sm font-semibold text-navy-900">{c.course_code}</span>
                        <span className="text-sm text-navy-600 truncate">{c.title}</span>
                        <span className={`text-2xs font-bold px-2 py-0.5 rounded-full border ${
                          c.is_active
                            ? 'bg-emerald-50 text-emerald-700 border-emerald-200'
                            : 'bg-surface-100 text-navy-500 border-surface-200'
                        }`}>
                          {c.is_active ? 'Active' : 'Archived'}
                        </span>
                      </div>
                      <p className="text-xs text-navy-400 mt-0.5">
                        {c.teacher_name || 'No teacher'} · {c.quiz_count} quiz{c.quiz_count === 1 ? '' : 'zes'}
                      </p>
                    </div>
                    <button
                      type="button"
                      disabled={busy === `course-${c.id}`}
                      onClick={() => download(
                        `course-${c.id}`,
                        () => historyAPI.exportCourse(c.id),
                        `${c.course_code}_results.xlsx`,
                      )}
                      className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg border border-surface-200 text-xs font-semibold text-navy-700 hover:bg-surface-50 disabled:opacity-60"
                    >
                      <Download className="w-3.5 h-3.5" />
                      {busy === `course-${c.id}` ? 'Preparing...' : 'Excel'}
                    </button>
                  </li>
                ))}
              </ul>
            </section>
          )
        })
      )}
    </div>
  )
}
