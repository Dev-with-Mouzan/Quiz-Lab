import axios from 'axios'

const API_BASE_URL = '/api'

const api = axios.create({
  baseURL: API_BASE_URL,
  headers: { 'Content-Type': 'application/json' },
})

// Attach JWT token to every request
api.interceptors.request.use((config) => {
  const token = localStorage.getItem('token')
  if (token) {
    config.headers.Authorization = `Bearer ${token}`
  }
  return config
})

// Handle 401 errors globally
api.interceptors.response.use(
  (response) => response,
  (error) => {
    const isLoginAttempt = error.config?.url?.includes('/auth/login') ||
      error.config?.url?.includes('/auth/verify-otp') ||
      error.config?.url?.includes('/auth/resend-otp')
    if (error.response?.status === 401 && !isLoginAttempt) {
      localStorage.removeItem('token')
      localStorage.removeItem('user')
      localStorage.removeItem('pendingVerification')
      window.location.href = '/login'
    }
    return Promise.reject(error)
  }
)

// ── Auth API ─────────────────────────────────────────
export const authAPI = {
  login: (data) => api.post('/auth/login', data),
  register: (data) => api.post('/auth/register', data),
  verifyOTP: (data) => api.post('/auth/verify-otp', data),
  resendOTP: (data) => api.post('/auth/resend-otp', data),
  forgotPassword: (data) => api.post('/auth/forgot-password', data),
  resendResetOTP: (data) => api.post('/auth/forgot-password', data),
  resetPassword: (data) => api.post('/auth/reset-password', data),
  getMe: () => api.get('/auth/me'),
}

// ── Users API (admin) ────────────────────────────────
export const usersAPI = {
  list: (params) => api.get('/users/', { params }),
  create: (data) => api.post('/users/', data),
  update: (id, data) => api.put(`/users/${id}`, data),
  hardDelete: (id) => api.delete(`/users/${id}/hard`),
  getStats: () => api.get('/users/stats/dashboard'),
  getProfile: (id) => api.get(`/users/${id}/profile`),
  getSemesterProgress: (id) => api.get(`/users/${id}/semester-progress`),
}

// ── Promotion API (admin) ─────────────────────────────
export const promotionAPI = {
  getSessions: (sessionType) => api.get('/users/promotion/sessions', { params: sessionType ? { session_type: sessionType } : {} }),
  getSessionSemesters: (session, sessionType) => api.get(`/users/promotion/sessions/${session}/semesters`, { params: sessionType ? { session_type: sessionType } : {} }),
  getSemesterStudents: (session, semester, sessionType) => api.get(`/users/promotion/sessions/${session}/semesters/${semester}`, { params: sessionType ? { session_type: sessionType } : {} }),
  promote: (data) => api.post('/users/promotion/promote', data),
  graduate: (data) => api.post('/users/promotion/graduate', data),
  getHistory: (session) => api.get('/users/promotion/history', { params: session ? { session } : {} }),
}

// ── Courses API ──────────────────────────────────────
export const coursesAPI = {
  list: (params) => api.get('/courses/', { params }),
  create: (data) => api.post('/courses/', data),
  update: (id, data) => api.put(`/courses/${id}`, data),
  delete: (id) => api.delete(`/courses/${id}`),
}

// ── Quizzes API ──────────────────────────────────────
export const quizzesAPI = {
  list: (params) => api.get('/quizzes', { params }),
  get: (id) => api.get(`/quizzes/${id}`),
  // Preview-parse a question-bank file (docx/csv/xlsx) before creating
  parseFile: (file) => {
    const formData = new FormData()
    formData.append('file', file)
    return api.post('/quizzes/parse-file', formData, {
      headers: { 'Content-Type': 'multipart/form-data' },
    })
  },
  // Create: data may be FormData (file upload) or plain object (manual questions)
  create: (data) => {
    if (data instanceof FormData) {
      return api.post('/quizzes', data, {
        headers: { 'Content-Type': 'multipart/form-data' },
      })
    }
    return api.post('/quizzes', data)
  },
  delete: (id) => api.delete(`/quizzes/${id}`),
  submit: (quizId, answers, timedOut = false) =>
    api.post(`/quizzes/${quizId}/submit`, { answers, timed_out: timedOut }),
  getAttempt: (quizId) => api.get(`/quizzes/${quizId}/attempts`),
  getAllAttempts: (quizId, includeAbsent = false) =>
    api.get(`/quizzes/${quizId}/all-attempts`, { params: { include_absent: includeAbsent } }),
  exportResults: (quizId) => api.get(`/quizzes/${quizId}/export`, { responseType: 'blob' }),
}
