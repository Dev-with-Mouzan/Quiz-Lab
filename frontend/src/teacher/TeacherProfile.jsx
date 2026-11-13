import { useState, useEffect } from 'react'
import { aiAPI } from '../services/api'
import { useAuth } from '../context/AuthContext'
import {
  Sparkles, KeyRound, CheckCircle2, AlertCircle, Loader2, Mail, ShieldCheck, Trash2,
} from 'lucide-react'

const inputClass =
  'w-full px-4 py-2.5 bg-white border border-surface-200 rounded-xl text-sm text-navy-900 placeholder-navy-300 focus:outline-none focus:ring-2 focus:ring-accent-400/30 focus:border-accent-400'

function initials(user) {
  const name = `${user?.first_name || ''} ${user?.last_name || ''}`.trim()
  if (!name) return (user?.email || '?')[0].toUpperCase()
  return name.split(/\s+/).slice(0, 2).map((w) => w[0].toUpperCase()).join('')
}

export default function TeacherProfile() {
  const { user } = useAuth()
  const [loading, setLoading] = useState(true)
  const [saving, setSaving] = useState(false)
  const [testing, setTesting] = useState(false)
  const [providers, setProviders] = useState([])
  const [savedProvider, setSavedProvider] = useState(null)
  const [savedModel, setSavedModel] = useState(null)
  const [provider, setProvider] = useState('')
  const [model, setModel] = useState('')
  const [apiKey, setApiKey] = useState('')
  const [hasKey, setHasKey] = useState(false)
  const [keyHint, setKeyHint] = useState(null)
  const [message, setMessage] = useState('')
  const [error, setError] = useState('')

  const currentProvider = providers.find((p) => p.id === provider)
  const savedProviderName = providers.find((p) => p.id === savedProvider)?.name
  const isReady = hasKey && !!savedProvider

  const applyServerState = (d) => {
    setProviders(d.providers)
    setSavedProvider(d.provider)
    setSavedModel(d.model)
    setProvider(d.provider || d.providers[0]?.id || '')
    setModel(d.model || d.providers[0]?.models[0] || '')
    setHasKey(d.has_key)
    setKeyHint(d.key_hint)
  }

  useEffect(() => {
    aiAPI.getSettings()
      .then((r) => applyServerState(r.data))
      .catch((err) => setError(err.response?.data?.detail || 'Could not load your AI settings'))
      .finally(() => setLoading(false))
  }, [])

  const onProviderChange = (id) => {
    setProvider(id)
    setModel(providers.find((p) => p.id === id)?.models[0] || '') // models don't carry over
    setMessage('')
    setError('')
  }

  const handleSave = async (e) => {
    e.preventDefault()
    setSaving(true)
    setError('')
    setMessage('')
    try {
      await aiAPI.saveSettings({ provider, model, api_key: apiKey || null })
      setApiKey('')
      const fresh = await aiAPI.getSettings()
      applyServerState(fresh.data)
      setMessage('Settings saved.')
    } catch (err) {
      setError(err.response?.data?.detail || 'Could not save your AI settings')
    } finally {
      setSaving(false)
    }
  }

  const handleTest = async () => {
    setTesting(true)
    setError('')
    setMessage('')
    try {
      // Test what is on screen, not what was last saved
      const r = await aiAPI.testSettings({ provider, model, api_key: apiKey || null })
      setMessage(r.data.message)
    } catch (err) {
      setError(err.response?.data?.detail || 'The test call failed')
    } finally {
      setTesting(false)
    }
  }

  const handleRemoveKey = async () => {
    setError('')
    setMessage('')
    try {
      await aiAPI.removeKey()
      setHasKey(false)
      setKeyHint(null)
      setMessage('Saved API key removed.')
    } catch (err) {
      setError(err.response?.data?.detail || 'Could not remove the key')
    }
  }

  if (loading) {
    return (
      <div className="flex items-center justify-center py-20">
        <Loader2 className="w-6 h-6 text-accent-500 animate-spin" />
      </div>
    )
  }

  return (
    <div className="max-w-3xl mx-auto space-y-6">
      {/* ── Account header ── */}
      <section className="border border-surface-200 rounded-2xl bg-white p-6 flex items-center gap-5">
        <span className="w-16 h-16 rounded-2xl bg-navy-950 text-accent-400 font-extrabold text-xl flex items-center justify-center shrink-0">
          {initials(user)}
        </span>
        <div className="min-w-0 flex-1">
          <div className="flex items-center gap-3 flex-wrap">
            <h1 className="text-xl font-extrabold text-navy-900 tracking-tight truncate">
              {user?.first_name} {user?.last_name}
            </h1>
            <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full bg-accent-50 text-accent-700 border border-accent-200 text-2xs font-bold uppercase tracking-wider">
              <ShieldCheck className="w-3 h-3" />
              Teacher
            </span>
          </div>
          <p className="text-sm text-navy-400 mt-1 flex items-center gap-1.5 truncate">
            <Mail className="w-3.5 h-3.5 shrink-0" />
            {user?.email}
          </p>
        </div>
      </section>

      {/* ── AI quiz assistant ── */}
      <section className="border border-surface-200 rounded-2xl bg-white overflow-hidden">
        <div className="px-6 py-5 border-b border-surface-100 flex items-start justify-between gap-4 flex-wrap">
          <div className="flex items-start gap-3">
            <span className="w-10 h-10 rounded-xl bg-accent-500/10 border border-accent-200 flex items-center justify-center shrink-0">
              <Sparkles className="w-5 h-5 text-accent-600" />
            </span>
            <div>
              <h2 className="text-base font-bold text-navy-900">AI quiz assistant</h2>
              <p className="text-sm text-navy-400 mt-0.5">
                Draft quiz questions with your own provider key. Drafts are saved only when you create a quiz.
              </p>
            </div>
          </div>
          <span className={`inline-flex items-center gap-1.5 px-3 py-1 rounded-full text-xs font-bold border ${
            isReady
              ? 'bg-emerald-50 text-emerald-700 border-emerald-200'
              : 'bg-amber-50 text-amber-700 border-amber-200'
          }`}>
            <span className={`w-1.5 h-1.5 rounded-full ${isReady ? 'bg-emerald-500' : 'bg-amber-500'}`} />
            {isReady ? 'Ready' : 'Not set up'}
          </span>
        </div>

        {/* Saved state */}
        <div className="px-6 py-4 bg-surface-50 border-b border-surface-100 flex items-center justify-between gap-4 flex-wrap">
          {hasKey ? (
            <p className="text-sm text-navy-600">
              Using <span className="font-semibold text-navy-900">{savedProviderName}</span>
              {savedModel && <> · <span className="font-mono text-xs">{savedModel}</span></>}
              {' '}· key ending <span className="font-mono font-semibold">{keyHint}</span>
            </p>
          ) : (
            <p className="text-sm text-navy-500">No API key saved yet. Choose a provider and add your key below.</p>
          )}
          {hasKey && (
            <button
              type="button"
              onClick={handleRemoveKey}
              className="inline-flex items-center gap-1.5 text-xs font-semibold text-danger-dark hover:underline"
            >
              <Trash2 className="w-3.5 h-3.5" />
              Remove saved key
            </button>
          )}
        </div>

        <form onSubmit={handleSave} className="px-6 py-6 space-y-6">
          {/* Provider */}
          <div>
            <p className="input-label">Provider</p>
            <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
              {providers.map((p) => {
                const selected = p.id === provider
                return (
                  <button
                    key={p.id}
                    type="button"
                    onClick={() => onProviderChange(p.id)}
                    className={`px-4 py-3 rounded-xl border text-left text-sm font-semibold transition-colors ${
                      selected
                        ? 'border-accent-400 bg-accent-50 text-navy-900 ring-2 ring-accent-400/30'
                        : 'border-surface-200 bg-white text-navy-600 hover:border-navy-300'
                    }`}
                  >
                    {p.name}
                  </button>
                )
              })}
            </div>
          </div>

          {/* Model */}
          <div>
            <label className="input-label" htmlFor="ai-model">Model</label>
            <input
              id="ai-model"
              list="ai-model-options"
              value={model}
              onChange={(e) => setModel(e.target.value)}
              className={`${inputClass} font-mono`}
              placeholder="Choose a model or type its name"
              required
            />
            <datalist id="ai-model-options">
              {(currentProvider?.models || []).map((m) => <option key={m} value={m} />)}
            </datalist>
            {currentProvider?.models?.length > 0 && (
              <div className="flex flex-wrap gap-2 mt-2">
                {currentProvider.models.map((m) => (
                  <button
                    key={m}
                    type="button"
                    onClick={() => setModel(m)}
                    className={`px-2.5 py-1 rounded-lg text-xs font-mono border transition-colors ${
                      model === m
                        ? 'bg-navy-950 text-accent-400 border-navy-950'
                        : 'bg-white text-navy-500 border-surface-200 hover:border-navy-300'
                    }`}
                  >
                    {m}
                  </button>
                ))}
              </div>
            )}
          </div>

          {/* API key */}
          <div>
            <label className="input-label" htmlFor="ai-key">API key</label>
            <div className="relative">
              <KeyRound className="w-4 h-4 text-navy-300 absolute left-3.5 top-1/2 -translate-y-1/2" />
              <input
                id="ai-key"
                type="password"
                autoComplete="off"
                value={apiKey}
                onChange={(e) => setApiKey(e.target.value)}
                className={`${inputClass} pl-11`}
                placeholder={hasKey ? 'Paste a new key to replace the saved one' : 'Paste your API key'}
              />
            </div>
            <p className="text-xs text-navy-400 mt-1.5">
              Stored encrypted on the server. It is never shown again after you save it.
              {savedProvider && provider !== savedProvider && ' A key is needed for the newly selected provider.'}
            </p>
          </div>

          {error && (
            <div className="flex items-start gap-2 bg-danger-light text-danger-dark px-4 py-3 rounded-xl text-sm font-medium border border-danger/20">
              <AlertCircle className="w-4 h-4 mt-0.5 shrink-0" />
              <span>{error}</span>
            </div>
          )}
          {message && (
            <div className="flex items-start gap-2 bg-success-light text-success-dark px-4 py-3 rounded-xl text-sm font-medium border border-success/20">
              <CheckCircle2 className="w-4 h-4 mt-0.5 shrink-0" />
              <span>{message}</span>
            </div>
          )}

          <div className="flex flex-wrap items-center justify-end gap-3 pt-2 border-t border-surface-100">
            <button
              type="button"
              onClick={handleTest}
              disabled={testing || (!hasKey && !apiKey)}
              className="px-5 py-2.5 text-sm font-semibold rounded-xl border border-surface-200 text-navy-700 hover:bg-surface-50 disabled:opacity-50 disabled:cursor-not-allowed"
            >
              {testing ? 'Testing...' : 'Test connection'}
            </button>
            <button type="submit" disabled={saving} className="btn-primary px-6 py-2.5 text-sm">
              {saving ? 'Saving...' : 'Save settings'}
            </button>
          </div>
        </form>
      </section>
    </div>
  )
}
