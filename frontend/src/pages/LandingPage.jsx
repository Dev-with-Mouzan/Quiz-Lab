import { useState, useEffect, useRef } from 'react'
import { Link } from 'react-router-dom'
import { AnimatedSection, StaggerContainer } from '../hooks/useScrollReveal.jsx'
import {
  GraduationCap,
  BookOpen,
  Users,
  BarChart3,
  ChevronDown,
  ChevronUp,
  Menu,
  X,
  ArrowRight,
  CheckCircle2,
  Clock,
  FileText,
  AlertTriangle,
  TrendingUp,
  Shield,
  Zap,
  Star,
  Mail,
  Phone,
  MapPin,
  Facebook,
  Instagram,
  Twitter,
  Youtube,
  UserPlus,
  ChevronLeft,
  ChevronRight,
  Shuffle,
} from 'lucide-react'

/* ─────────────────────────────── Navbar ─────────────────────────────── */
function Navbar() {
  const [scrolled, setScrolled] = useState(false)
  const [mobileOpen, setMobileOpen] = useState(false)
  const [activeSection, setActiveSection] = useState('hero')

  useEffect(() => {
    const handler = () => setScrolled(window.scrollY > 40)
    window.addEventListener('scroll', handler, { passive: true })
    return () => window.removeEventListener('scroll', handler)
  }, [])

  // Track which section is in view
  useEffect(() => {
    const sectionIds = ['hero', 'problem', 'solution', 'faculty', 'how-it-works', 'faq']
    const observers = []

    sectionIds.forEach((id) => {
      const el = document.getElementById(id)
      if (!el) return

      const observer = new IntersectionObserver(
        ([entry]) => {
          if (entry.isIntersecting) {
            setActiveSection(id)
          }
        },
        { rootMargin: '-40% 0px -55% 0px', threshold: 0 }
      )

      observer.observe(el)
      observers.push(observer)
    })

    return () => observers.forEach((o) => o.disconnect())
  }, [])

  const links = [
    { label: 'Home', href: '#hero', id: 'hero' },
    { label: 'About', href: '#problem', id: 'problem' },
    { label: 'Features', href: '#solution', id: 'solution' },
    { label: 'Faculty', href: '#faculty', id: 'faculty' },
    { label: 'How It Works', href: '#how-it-works', id: 'how-it-works' },
    { label: 'FAQ', href: '#faq', id: 'faq' },
  ]

  const s = scrolled

  return (
    <nav
      className={`fixed top-0 inset-x-0 z-50 transition-all duration-300 ${
        s
          ? 'bg-surface-0/95 backdrop-blur-md shadow-card border-b border-surface-200/60'
          : 'bg-white/5 backdrop-blur-sm'
      }`}
    >
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="flex items-center justify-between h-14 lg:h-16">
          <a href="#hero" className="flex items-center gap-3 group min-w-0">
            <img src="/college-logo.png" alt="GGCB Logo" className="w-8 h-8 lg:w-9 lg:h-9 rounded-lg object-cover shrink-0" />
            <div className="min-w-0">
              <p className={`text-xs sm:text-sm lg:text-base font-bold leading-tight tracking-tight truncate transition-colors duration-300 ${s ? 'text-navy-900' : 'text-white'}`}>
                QuizLab
              </p>
              <p className={`text-xs font-medium truncate transition-colors duration-300 ${s ? 'text-navy-600' : 'text-white/50'}`}>
                Govt. Graduate College Burewala
              </p>
            </div>
          </a>

          <div className="hidden lg:flex items-center gap-1">
            {links.map((l) => (
              <a
                key={l.href}
                href={l.href}
                className={`px-4 py-3 text-sm font-medium rounded-t-lg transition-all duration-200 ${
                  activeSection === l.id
                    ? s
                      ? 'text-navy-900 font-semibold border-b-2 border-accent-500 rounded-none'
                      : 'text-white font-semibold border-b-2 border-accent-400 rounded-none'
                    : s
                      ? 'text-navy-400 hover:text-navy-900 hover:bg-surface-100'
                      : 'text-white/60 hover:text-white'
                }`}
              >
                {l.label}
              </a>
            ))}
          </div>

          <div className="hidden lg:flex items-center gap-3">
            <Link
              to="/login"
              className={`text-sm font-medium px-4 py-2 rounded-lg transition-colors duration-300 ${
                s ? 'text-navy-600 hover:text-navy-900 hover:bg-surface-100' : 'text-white/80 hover:text-white'
              }`}
            >
              Sign In
            </Link>
            <Link to="/register" className={`inline-flex items-center gap-2 px-5 py-2.5 rounded-xl text-sm font-semibold transition-colors duration-300 ${
              s ? 'bg-accent-500 text-black hover:bg-accent-400' : 'bg-accent-500 text-black hover:bg-accent-400'
            }`}>
              Get Started
              <ArrowRight className="w-4 h-4" />
            </Link>
          </div>

          <button
            onClick={() => setMobileOpen(!mobileOpen)}
            className={`lg:hidden p-2 rounded-lg transition-colors ${
              s ? 'hover:bg-surface-100' : 'hover:bg-white/10'
            }`}
            aria-label="Toggle menu"
          >
            {mobileOpen ? (
              <X className={`w-5 h-5 transition-colors ${s ? 'text-navy-600' : 'text-white'}`} />
            ) : (
              <Menu className={`w-5 h-5 transition-colors ${s ? 'text-navy-600' : 'text-white'}`} />
            )}
          </button>
        </div>
      </div>

      {mobileOpen && (
        <div className="lg:hidden bg-surface-0/98 backdrop-blur-md border-b border-surface-200 shadow-elevated">
          <div className="px-4 py-4 space-y-1">
            {links.map((l) => (
              <a
                key={l.href}
                href={l.href}
                onClick={() => setMobileOpen(false)}
                className="block px-4 py-2.5 text-sm font-medium text-navy-600 hover:text-navy-900 hover:bg-surface-100 rounded-lg transition-colors"
              >
                {l.label}
              </a>
            ))}
            <div className="pt-3 border-t border-surface-200 mt-2 flex flex-col gap-2">
              <Link to="/login" onClick={() => setMobileOpen(false)} className="text-sm font-medium text-navy-600 hover:text-navy-900 px-4 py-2.5 rounded-lg border border-surface-200 text-center transition-colors">
                Sign In
              </Link>
              <Link to="/register" onClick={() => setMobileOpen(false)} className="inline-flex items-center justify-center gap-2 px-5 py-2.5 rounded-xl text-sm font-semibold border border-surface-200 text-navy-600 hover:bg-surface-100 hover:text-navy-900 transition-colors"
              >
                Get Started
                <ArrowRight className="w-4 h-4" />
              </Link>
            </div>
          </div>
        </div>
      )}
    </nav>
  )
}

/* ─────────────────────────────── Hero ─────────────────────────────── */
function Hero() {
  const [profileIndex, setProfileIndex] = useState(0)
  const [fading, setFading] = useState(false)

  const profiles = [
    {
      name: 'Ali Hassan',
      score: '88%', attempts: '5', correct: '9/10',
      bars: [40, 65, 55, 80, 70, 90, 75],
      quiz: 'Data Structures — Quiz 3',
      due: 'Scored 9/10',
    },
    {
      name: 'Fatima Zahra',
      score: '96%', attempts: '7', correct: '10/10',
      bars: [70, 85, 80, 95, 88, 92, 90],
      quiz: 'Operating Systems — Quiz 2',
      due: 'Scored 10/10',
    },
    {
      name: 'Qasim Ali',
      score: '74%', attempts: '3', correct: '7/10',
      bars: [30, 50, 60, 45, 70, 55, 65],
      quiz: 'Database Systems — Quiz 4',
      due: 'Due tomorrow',
    },
    {
      name: 'Ayesha Bibi',
      score: '91%', attempts: '6', correct: '13/15',
      bars: [60, 75, 85, 70, 80, 95, 88],
      quiz: 'AI & Machine Learning — Quiz 1',
      due: 'Due today',
    },
    {
      name: 'Hassan Raza',
      score: '82%', attempts: '4', correct: '8/10',
      bars: [45, 55, 70, 60, 75, 80, 65],
      quiz: 'Networking — Quiz 2',
      due: 'Scored 8/10',
    },
    {
      name: 'Zainab Fatima',
      score: '99%', attempts: '8', correct: '15/15',
      bars: [90, 95, 88, 92, 97, 100, 94],
      quiz: 'CS — Midterm Practice Quiz',
      due: 'Submitted ✓',
    },
  ]

  // Cycle profiles every 5 seconds with fade transition
  useEffect(() => {
    const interval = setInterval(() => {
      setFading(true)
      setTimeout(() => {
        setProfileIndex((prev) => (prev + 1) % profiles.length)
        setFading(false)
      }, 300)
    }, 5000)
    return () => clearInterval(interval)
  }, [])

  const p = profiles[profileIndex]

  return (
    <section
      id="hero"
      className="relative h-[100dvh] min-h-[600px] flex items-center overflow-hidden"
    >
      {/* Background image */}
      <div className="absolute inset-0">
        <img
          src="/college_image.jfif"
          alt="Govt. Graduate College Burewala"
          className="w-full h-full object-cover object-center"
          loading="eager"
        />
        <div className="absolute inset-0 bg-navy-950/90" />
      </div>

      <div className="relative max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 pt-32 pb-20 lg:pt-40 lg:pb-28 w-full">
        <div className="max-w-3xl mx-auto lg:mx-0 text-center lg:text-left">
          <div className="hero-animate inline-flex items-center gap-2 px-4 py-1.5 rounded-full border border-white/10 bg-white/5 mb-8">
            <Star className="w-3.5 h-3.5 text-accent-400" />
            <span className="text-xs font-semibold text-white/60 tracking-wide">
              Dept. of Computer Science · Govt. Graduate College Burewala
            </span>
          </div>

          <h1 className="hero-animate text-5xl sm:text-6xl lg:text-7xl font-extrabold text-white leading-[1.05] tracking-tight">
            Smarter Quizzes,
            <br />
            <span className="text-accent-400">Instant Grades.</span>
          </h1>

          <p className="hero-animate mt-7 text-lg lg:text-xl text-white/50 max-w-lg leading-relaxed mx-auto lg:mx-0">
            Question banks, shuffled quizzes, and instant grading — all in
            one platform. Built for the CS Department at Govt. Graduate College Burewala.
          </p>

          <div className="hero-animate mt-10 flex flex-wrap gap-4 justify-center lg:justify-start">
            <Link
              to="/register"
              className="inline-flex items-center gap-2 px-8 py-3.5 rounded-xl text-base font-bold bg-accent-500 text-black hover:bg-accent-400 transition-all duration-200 shadow-lg shadow-accent-500/20"
            >
              Get Started Free
              <ArrowRight className="w-5 h-5" />
            </Link>
            <a
              href="#how-it-works"
              className="inline-flex items-center gap-2 px-8 py-3.5 rounded-xl text-base font-semibold text-white border-2 border-white/25 hover:bg-white/10 transition-all duration-200"
            >
              See How It Works
            </a>
          </div>

          <div className="hero-animate mt-14 flex items-center gap-8 lg:gap-10 justify-center lg:justify-start">
            {[
              { value: '2', label: 'Labs' },
              { value: '500+', label: 'CS Students' },
              { value: '07+', label: 'Faculty Members' },
            ].map((s, i) => (
              <div key={s.label} className="relative flex flex-col items-center text-center">
                {i > 0 && <div className="absolute -left-4 lg:-left-6 top-1/2 -translate-y-1/2 w-px h-8 bg-white/10 hidden lg:block" />}
                <p className="text-3xl font-extrabold text-white">{s.value}</p>
                <p className="text-sm text-white/50 font-semibold mt-0.5 uppercase tracking-wider">{s.label}</p>
              </div>
            ))}
          </div>
        </div>

        {/* ── Right: Animated Dashboard Card ── */}
        <div className="hidden lg:block absolute right-8 xl:right-16 top-1/2 -translate-y-1/2">
          <div className="relative w-[420px]">
            {/* Background shadow card */}
            <div className="card-fade-in absolute top-6 left-6 w-full h-[320px] rounded-2xl border border-white/5 bg-white/[0.02]" style={{ animationDelay: '0.5s' }} />

            {/* Main card */}
            <div className="card-slide-in relative rounded-2xl border border-white/10 bg-white/[0.04] backdrop-blur-sm p-7">
              {/* Window dots */}
              <div className="dot-fade-in flex items-center gap-2 mb-6" style={{ animationDelay: '0.8s' }}>
                <div className="dot-cycle-1 w-3 h-3 rounded-full bg-white/10" />
                <div className="dot-cycle-2 w-3 h-3 rounded-full bg-white/10" />
                <div className="dot-cycle-3 w-3 h-3 rounded-full bg-white/10" />
                <div className="ml-auto">
                  <img src="/college-logo.png" alt="GGCB" className="w-8 h-8 rounded-full object-cover" />
                </div>
              </div>

              {/* Greeting — fades between profiles */}
              <div className={`mb-5 transition-opacity duration-300 ${fading ? 'opacity-0' : 'opacity-100'}`}>
                <p className="text-sm text-white/40 mb-1">Welcome back,</p>
                <p className="text-lg font-bold text-white">{p.name}</p>
              </div>

              {/* Stat pills */}
              <div className="grid grid-cols-3 gap-3 mb-5">
                {[
                  { label: 'Score', value: p.score, accent: true },
                  { label: 'Attempts', value: p.attempts, accent: false },
                  { label: 'Correct', value: p.correct, accent: false },
                ].map((s) => (
                  <div
                    key={s.label}
                    className={`rounded-xl p-3 text-center transition-all duration-300 ${
                      s.accent ? 'bg-accent-500/15 border border-accent-500/20 stat-pulse' : 'bg-white/5'
                    } ${fading ? 'opacity-50 scale-95' : 'opacity-100 scale-100'}`}
                  >
                    <p className={`text-lg font-bold ${s.accent ? 'text-accent-400' : 'text-white'} transition-all duration-300`}>{s.value}</p>
                    <p className="text-xs text-white/30 mt-0.5">{s.label}</p>
                  </div>
                ))}
              </div>

              {/* Bar chart — bars morph between profiles */}
              <div className="bg-white/5 rounded-xl p-4 mb-4">
                <div className="flex items-end gap-2 h-28">
                  {p.bars.map((h, i) => (
                    <div key={i} className="flex-1 flex flex-col items-center gap-1">
                      {/* Bar */}
                      <div className="w-full rounded-t-md overflow-hidden" style={{ height: '60px' }}>
                        <div
                          className="w-full rounded-t-md transition-all duration-700 ease-out"
                          style={{
                            height: `${h}%`,
                            marginTop: 'auto',
                            background: i === 5
                              ? 'linear-gradient(to top, #f59e0b, #fbbf24)'
                              : h >= 80
                                ? 'linear-gradient(to top, rgba(251,191,36,0.3), rgba(251,191,36,0.5))'
                                : 'linear-gradient(to top, rgba(255,255,255,0.08), rgba(255,255,255,0.15))',
                          }}
                        />
                      </div>
                    </div>
                  ))}
                </div>
              </div>

              {/* Quiz row — fades between profiles */}
              <div className={`flex items-center gap-3 bg-white/5 rounded-xl px-4 py-3 transition-opacity duration-300 ${fading ? 'opacity-0' : 'opacity-100'}`}>
                <div className="w-8 h-8 rounded-lg bg-accent-500/15 flex items-center justify-center">
                  <FileText className="w-4 h-4 text-accent-400" />
                </div>
                <div className="flex-1 min-w-0">
                  <p className="text-xs font-medium text-white/80 truncate">{p.quiz}</p>
                  <p className="text-xs text-accent-400/80">{p.due}</p>
                </div>
                <CheckCircle2 className="w-4 h-4 text-white/15 shrink-0" />
              </div>
            </div>

            {/* Floating dots */}
            <div className="absolute -top-3 -right-3 w-6 h-6 rounded-full bg-accent-500/30 animate-[float_4s_ease-in-out_infinite]" />
            <div className="absolute -bottom-2 -left-4 w-4 h-4 rounded-full bg-accent-500/20 animate-[float_5s_ease-in-out_infinite] [animation-delay:1s]" />
          </div>
        </div>
      </div>
    </section>
  )
}

/* ─────────────────────────── Social Proof ─────────────────────────── */
function SocialProof() {
  const stats = [
    { icon: Users, value: '500+', label: 'CS Students', description: 'Currently enrolled in Computer Science programs' },
    { icon: BookOpen, value: '25+', label: 'CS Courses', description: 'Data Structures, AI, Networks, DB & more' },
    { icon: Zap, value: 'Instant', label: 'Auto-Grading', description: 'Score and answer review the moment you submit' },
    { icon: FileText, value: '3 Formats', label: 'Question Banks', description: 'DOCX, CSV and XLSX uploads supported' },
  ]

  return (
    <section className="py-20 lg:py-28 bg-surface-50">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <AnimatedSection className="text-center mb-16">
          <p className="inline-flex items-center gap-2 px-4 py-1.5 rounded-full border border-accent-200 bg-accent-50 text-accent-600 text-xs font-bold tracking-widest mb-3">Trusted by CS Students & Faculty</p>
          <h2 className="text-display-sm lg:text-display-md text-navy-900">Powering Computer Science at GGCB</h2>
          <p className="mt-3 text-navy-400 max-w-2xl mx-auto">
            Real numbers, real impact — see how QuizLab runs daily quizzing for the CS Department at Govt. Graduate College Burewala.
          </p>
        </AnimatedSection>

        <StaggerContainer className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-8">
          {stats.map((s) => (
            <div key={s.label} className="stagger-child bg-white rounded-2xl border border-surface-200 p-8 text-center shadow-card group hover:-translate-y-2 hover:shadow-elevated hover:border-accent-200 transition-all duration-300">
              <div className="w-16 h-16 rounded-2xl bg-accent-50 border border-accent-100 flex items-center justify-center mx-auto mb-6 group-hover:bg-accent-100 group-hover:scale-110 transition-all duration-300">
                <s.icon className="w-8 h-8 text-accent-600" />
              </div>
              <p className="text-4xl font-extrabold text-navy-900 tracking-tight">{s.value}</p>
              <p className="text-sm font-bold text-navy-600 mt-2">{s.label}</p>
              <p className="text-xs text-navy-400 mt-3 leading-relaxed">{s.description}</p>
            </div>
          ))}
        </StaggerContainer>
      </div>
    </section>
  )
}

/* ───────────────────────── Problem Statement ───────────────────────── */
function ProblemStatement() {
  const problems = [
    { icon: Clock, title: 'Slow Marking Cycles', description: 'Paper quizzes sit in a stack for days or weeks while teachers mark them by hand. Students forget what they got wrong by the time the result finally arrives.' },
    { icon: AlertTriangle, title: 'Identical Papers', description: 'Every student receiving the exact same paper makes sharing answers trivial. One photo in a WhatsApp group and the whole class has the key.' },
    { icon: FileText, title: 'Lost Question Papers', description: 'Question papers live in notebooks, Word files and printed handouts. Last year’s quiz is impossible to find, let alone reuse for practice.' },
    { icon: TrendingUp, title: 'No Performance Records', description: 'Without data, neither students nor teachers can track progress across the semester. Weak topics stay invisible until it is too late.' },
  ]

  return (
    <section id="problem" className="py-20 lg:py-28 bg-surface-0">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <AnimatedSection className="max-w-3xl mx-auto text-center mb-16">
          <p className="inline-flex items-center gap-2 px-4 py-1.5 rounded-full border border-accent-200 bg-accent-50 text-accent-600 text-xs font-bold uppercase tracking-widest mb-3">The Challenge</p>
          <h2 className="text-display-sm lg:text-display-md text-navy-900">
            Quizzing Shouldn't Feel <span className="text-accent-500">This Hard</span>
          </h2>
          <p className="mt-4 text-navy-400 text-lg leading-relaxed">
            Testing in the CS Department at Govt. Graduate College Burewala still relies on paper, hand marking and shared files. The result? Slow results, copied answers, and no record of who learned what.
          </p>
        </AnimatedSection>

        <StaggerContainer className="grid grid-cols-1 md:grid-cols-2 gap-6 sm:gap-8">
          {problems.map((p) => (
            <div key={p.title} className="stagger-child flex flex-col sm:flex-row sm:gap-5 gap-4 p-6 sm:p-7 rounded-2xl bg-white border border-surface-200 shadow-card hover:shadow-elevated hover:-translate-y-1 transition-all duration-300">
              <div className="w-12 h-12 sm:w-14 sm:h-14 rounded-xl bg-accent-50 border border-accent-200 flex items-center justify-center shrink-0 self-center sm:self-auto">
                <p.icon className="w-6 h-6 sm:w-7 sm:h-7 text-accent-600" />
              </div>
              <div className="text-center sm:text-left">
                <h3 className="text-base sm:text-lg font-bold text-navy-900">{p.title}</h3>
                <p className="text-sm text-navy-400 mt-2 leading-relaxed">{p.description}</p>
              </div>
            </div>
          ))}
        </StaggerContainer>
      </div>
    </section>
  )
}

/* ────────────────────────── Solution ────────────────────────── */
function Solution() {
  const features = [
    { icon: FileText, title: 'Question-Bank Uploads', description: 'Drop a DOCX, CSV or XLSX file and QuizLab parses every question and its answer key. Or write questions manually.', color: 'info' },
    { icon: Shuffle, title: 'Shuffled Per Student', description: 'Set how many questions each student receives — every attempt gets a different random subset in a different order.', color: 'accent' },
    { icon: Zap, title: 'Instant Auto-Grading', description: 'Submissions are scored the moment they come in. Students see their result and a full answer review right away.', color: 'success' },
    { icon: Users, title: 'Role-Based Access', description: 'Separate dashboards for Admins, Teachers, and Students. Everyone sees exactly what they need — nothing more.', color: 'warning' },
    { icon: Shield, title: 'Secure & Private', description: 'OTP-based authentication, encrypted sessions, and role-based permissions keep student records safe.', color: 'info' },
    { icon: Clock, title: 'Deadlines & Time Limits', description: 'Give every quiz a deadline and an optional time limit. Once the deadline passes, submissions close automatically.', color: 'accent' },
  ]

  const colorMap = {
    success: { bg: 'bg-success-light', icon: 'text-success' },
    info: { bg: 'bg-info-light', icon: 'text-info' },
    accent: { bg: 'bg-accent-50', icon: 'text-accent-600' },
    warning: { bg: 'bg-warning-light', icon: 'text-warning-dark' },
  }

  return (
    <section id="solution" className="relative py-20 lg:py-28 bg-navy-950 overflow-hidden">
      <div
        className="absolute inset-0 bg-cover bg-center"
        style={{ backgroundImage: "url('/lab.jfif')" }}
      />
      <div className="absolute inset-0 bg-gradient-to-b from-navy-950/100 via-navy-950/90 to-navy-900/95" />
      <div className="relative max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <AnimatedSection className="text-center mb-16">
          <p className="inline-flex items-center gap-2 px-4 py-1.5 rounded-full border border-white/10 bg-white/5 text-accent-400 text-xs font-bold uppercase tracking-widest mb-3">Our Solution</p>
          <h2 className="text-display-sm lg:text-display-md text-white">
            Everything You Need, <span className="text-accent-400">One Platform</span>
          </h2>
          <p className="mt-4 text-navy-200 max-w-2xl mx-auto">
            QuizLab is purpose-built for the CS Department at Govt. Graduate College Burewala — from question bank to graded result, all under one roof.
          </p>
        </AnimatedSection>

        <StaggerContainer className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-10">
          {features.map((f) => {
            const c = colorMap[f.color]
            return (
              <div key={f.title} className="stagger-child bg-navy-800/80 backdrop-blur-md border border-white/10 rounded-2xl p-7 hover:bg-navy-800 hover:border-white/20 hover:shadow-[0_8px_30px_rgba(0,0,0,0.3)] hover:-translate-y-1 transition-all duration-300 group">
                <div className={`w-14 h-14 rounded-xl ${c.bg} border border-white/10 flex items-center justify-center mb-5 group-hover:scale-110 transition-transform duration-300`}>
                  <f.icon className={`w-7 h-7 ${c.icon}`} />
                </div>
                <h3 className="text-lg font-bold text-white">{f.title}</h3>
                <p className="text-sm text-navy-200 mt-2.5 leading-relaxed">{f.description}</p>
              </div>
            )
          })}
        </StaggerContainer>
      </div>
    </section>
  )
}

/* ─────────────────────── How It Works ─────────────────────── */
function HowItWorks() {
  const [inView, setInView] = useState(false)

  useEffect(() => {
    const el = document.getElementById('how-it-works')
    if (!el) return
    const obs = new IntersectionObserver(
      ([e]) => { if (e.isIntersecting) setInView(true) },
      { threshold: 0.15 }
    )
    obs.observe(el)
    return () => obs.disconnect()
  }, [])

  const steps = [
    {
      step: 1,
      icon: UserPlus,
      title: 'Create Your Account',
      description: 'Sign up with your college email address. Verify your account with a one-time code sent to your email.',
      detail: 'Takes less than 30 seconds',
    },
    {
      step: 2,
      icon: BookOpen,
      title: 'Get Your Courses',
      description: 'Courses appear automatically based on your session and semester — Data Structures, OS, DB, and more.',
      detail: 'All courses ready on day one',
    },
    {
      step: 3,
      icon: BarChart3,
      title: 'Attempt & Track',
      description: 'Take your shuffled quiz subset, submit, and see your score with a full answer review — instantly.',
      detail: 'Results in seconds',
    },
  ]

  return (
    <section id="how-it-works" className="py-20 lg:py-28 bg-surface-50">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <AnimatedSection className="text-center mb-16">
          <p className="inline-flex items-center gap-2 px-4 py-1.5 rounded-full border border-accent-200 bg-accent-50 text-accent-600 text-xs font-bold tracking-widest mb-3">Simple & Intuitive</p>
          <h2 className="text-display-sm lg:text-display-md text-navy-900">How It Works</h2>
          <p className="mt-3 text-navy-400 max-w-2xl mx-auto">
            Getting started takes less than 2 minutes. Here's the journey from registration to your first graded quiz.
          </p>
        </AnimatedSection>

        {/* Step cards */}
        <div className="max-w-5xl mx-auto">
          <div className="grid grid-cols-1 md:grid-cols-3 gap-8 lg:gap-6 relative">
            {/* Connector line with animated particle (desktop only) */}
            <div className="hidden md:block absolute left-[20%] right-[20%] h-1 z-0" style={{ top: '32px' }}>
              {/* Background line */}
              <div className="h-full bg-surface-300" />
              {/* Animated fill */}
              <div className={`absolute inset-0 h-full bg-accent-400 transition-all duration-1000 ease-out ${inView ? 'w-full' : 'w-0'}`} />
              {/* Glowing particle */}
              {inView && (
                <div className="particle-trail absolute inset-0 h-full overflow-visible">
                  <div className="particle-glow absolute top-1/2 -translate-y-1/2" />
                </div>
              )}
            </div>

            {steps.map((step, i) => (
                <div
                  key={step.step}
                  className={`relative transition-all duration-700 ease-out ${
                    inView ? 'opacity-100 translate-y-0' : 'opacity-0 translate-y-8'
                  }`}
                  style={{ transitionDelay: `${i * 200}ms` }}
                >
                  <div className="text-center">
                    {/* Step number circle */}
                    <div className="relative inline-flex items-center justify-center mb-6">
                      <div className="w-16 h-16 rounded-2xl bg-accent-50 border border-accent-200 flex items-center justify-center relative z-10 transition-transform duration-500 hover:scale-110">
                        <step.icon className="w-7 h-7 text-accent-600" />
                      </div>
                      <span className="absolute -top-2 -right-2 w-7 h-7 rounded-full bg-accent-500 text-white text-xs font-bold flex items-center justify-center z-20 shadow-md">
                        {step.step}
                      </span>
                    </div>

                    {/* Content */}
                    <h3 className="text-lg font-bold text-navy-900 mb-2">{step.title}</h3>
                    <p className="text-sm text-navy-400 leading-relaxed max-w-xs mx-auto mb-3">
                      {step.description}
                    </p>
                    <div className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-full bg-white border border-surface-200">
                      <CheckCircle2 className="w-3.5 h-3.5 text-success" />
                      <span className="text-xs font-semibold text-navy-600">{step.detail}</span>
                    </div>
                  </div>
                </div>
              ))}
          </div>
        </div>
      </div>
    </section>
  )
}

/* ─────────────────────────── Faculty Carousel ─────────────────────────── */
function FacultyCarousel({ faculty }) {
  const [current, setCurrent] = useState(0)
  const [isPaused, setIsPaused] = useState(false)
  const timerRef = useRef(null)
  const maxIndex = Math.max(0, faculty.length - 3)
  const CARD_W = 334
  const GAP = 32
  const STEP = CARD_W + GAP

  const go = (dir) => {
    setCurrent((prev) => {
      const next = prev + dir
      if (next < 0) return maxIndex
      if (next > maxIndex) return 0
      return next
    })
  }

  useEffect(() => {
    if (isPaused) return
    timerRef.current = setInterval(() => go(1), 4000)
    return () => clearInterval(timerRef.current)
  }, [isPaused])

  return (
    <div
      className="relative mx-auto"
      style={{ maxWidth: '1100px', height: '420px' }}
      onMouseEnter={() => setIsPaused(true)}
      onMouseLeave={() => setIsPaused(false)}
    >
      {/* Track */}
      <div className="overflow-hidden h-full">
        <div
          className="flex h-full"
          style={{
            gap: `${GAP}px`,
            transform: `translateX(-${current * STEP}px)`,
            transition: 'transform 0.7s cubic-bezier(0.4, 0, 0.2, 1)',
          }}
        >
          {faculty.map((f) => (
            <div key={f.name} className="shrink-0 flex flex-col bg-white rounded-2xl border border-surface-200 overflow-hidden group hover:-translate-y-1 hover:shadow-lg transition-all duration-300" style={{ width: `${CARD_W}px`, height: '400px' }}>
              {/* Photo */}
              <div className="relative h-72 overflow-hidden">
                <img src={f.image} alt={f.name} className="w-full h-full object-cover object-top group-hover:scale-105 transition-transform duration-500" loading="lazy" onError={(e) => { e.target.style.display = 'none'; e.target.parentElement.classList.add('bg-gradient-to-br', 'from-accent-100', 'to-accent-200'); }} />
                <div className="absolute inset-x-0 bottom-0 h-28 bg-gradient-to-t from-black/90 via-black/50 to-transparent" />
                <div className="absolute bottom-3 left-4 right-4">
                  <p className="text-base font-bold text-white">{f.name}</p>
                  <p className="text-sm font-semibold text-accent-500">{f.title}</p>
                </div>
              </div>
              {/* Details */}
              <div className="flex-1 flex flex-col justify-between px-4 py-2.5">
                <div>
                  <div className="flex items-start gap-1.5 mb-1.5">
                    <GraduationCap className="w-3.5 h-3.5 text-accent-500 mt-0.5 shrink-0" />
                    <div>
                      <p className="text-xs font-semibold text-navy-600">{f.qualification}</p>
                      <p className="text-xs text-navy-400">{f.university}</p>
                    </div>
                  </div>
                  <div className="flex items-start gap-1.5">
                    <BookOpen className="w-3.5 h-3.5 text-accent-500 mt-0.5 shrink-0" />
                    <div className="flex flex-wrap gap-1">
                      {f.research.map((r) => (
                        <span key={r} className="text-xs font-medium px-2 py-0.5 rounded-full bg-accent-50 text-accent-700 border border-accent-100">{r}</span>
                      ))}
                    </div>
                  </div>
                </div>
                {f.email && (
                  <div className="flex items-center gap-1.5 pt-1.5 border-t border-surface-100">
                    <Mail className="w-3 h-3 text-accent-500 shrink-0" />
                    <a href={`mailto:${f.email}`} className="text-xs text-navy-600 hover:text-accent-600 transition-colors truncate">{f.email}</a>
                  </div>
                )}
              </div>
            </div>
          ))}
        </div>
      </div>

      {/* Left Arrow */}
      <button onClick={() => go(-1)} aria-label="Previous faculty" className="absolute left-0 top-1/2 -translate-y-1/2 -translate-x-10 z-20 w-10 h-10 rounded-full bg-white/90 border border-surface-200 shadow-md flex items-center justify-center hover:bg-white hover:shadow-lg transition-all cursor-pointer">
        <ChevronLeft className="w-5 h-5 text-navy-600" />
      </button>

      {/* Right Arrow */}
      <button onClick={() => go(1)} aria-label="Next faculty" className="absolute right-0 top-1/2 -translate-y-1/2 translate-x-10 z-20 w-10 h-10 rounded-full bg-white/90 border border-surface-200 shadow-md flex items-center justify-center hover:bg-white hover:shadow-lg transition-all cursor-pointer">
        <ChevronRight className="w-5 h-5 text-navy-600" />
      </button>
    </div>
  )
}

/* ─────────────────────────── Faculty ─────────────────────────── */
function Faculty() {
  const faculty = [
    {
      name: 'Dr. Rana Muhammad Nadeem',
      title: 'Associate Professor & HOD',
      department: 'Department of Computer Science',
      qualification: 'Ph.D. in Computer Science',
      university: 'The Superior University, Lahore',
      research: ['Machine Learning', 'Deep Learning', 'Internet of Things (IoT)'],
      email: 'dr.rananadim@ggcb.edu.pk',
      image: '/Dr Rana Nadeem sb HOD of computer science.png',
    },
    {
      name: 'Muhammad Imran',
      title: 'Lecturer & IT Focal Person',
      department: 'Department of Computer Science',
      qualification: 'MS in Computer Science',
      university: 'Govt. Graduate College Burewala',
      research: ['Web Development', 'IT Systems', 'Educational Technology'],
      email: 'imran.cs@ggcb.edu.pk',
      image: '/Prof Imran sb.png',
    },
    {
      name: 'Farah Mumtaz',
      title: 'Assistant Professor',
      department: 'Department of Computer Science',
      qualification: 'M.Phil in Computer Science',
      university: 'Govt. Graduate College Burewala',
      research: ['Software Engineering', 'Web Development'],
      email: 'farah.cs@ggcb.edu.pk',
      image: 'https://ggcb.edu.pk/uploads/staff/6a1afbda35ce5_1780153306.jpg',
    },
    {
      name: 'Mubashar Ahmad Shakeel',
      title: 'Assistant Professor',
      department: 'Department of Computer Science',
      qualification: 'MSc in Computer Science',
      university: 'Govt. Graduate College Burewala',
      research: ['Data Structures', 'Algorithms'],
      email: 'mubashar.cs@ggcb.edu.pk',
      image: '/Mubashir sb .png',
    },
    {
      name: 'Dr. Israr Ahmad',
      title: 'Lecturer',
      department: 'Department of Computer Science',
      qualification: 'Ph.D in Computer Science',
      university: 'Govt. Graduate College Burewala',
      research: ['Networks', 'Cloud Computing'],
      email: 'israr.cs@ggcb.edu.pk',
      image: '/DR Israr sb.png',
    },
    {
      name: 'Ali Rehan Alvi',
      title: 'Lecturer',
      department: 'Department of Computer Science',
      qualification: 'MSc in Computer Science',
      university: 'Govt. Graduate College Burewala',
      research: ['Programming', 'Database Systems'],
      email: 'ali.cs@ggcb.edu.pk',
      image: '/Prof Alvi sb.png',
    },
    {
      name: 'Myra Ashraf',
      title: 'Lecturer',
      department: 'Department of Computer Science',
      qualification: 'M.Phil in Computer Science',
      university: 'Govt. Graduate College Burewala',
      research: ['Artificial Intelligence', 'Data Science'],
      email: 'myra.cs@ggcb.edu.pk',
      image: 'https://ggcb.edu.pk/uploads/staff/6a1afeac984a9_1780154028.jpg',
    },
  ]

  return (
    <section id="faculty" className="py-20 lg:py-28 bg-surface-50">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <AnimatedSection className="text-center mb-16">
          <p className="inline-flex items-center gap-2 px-4 py-1.5 rounded-full border border-accent-200 bg-accent-50 text-accent-600 text-xs font-bold uppercase tracking-widest mb-3">Our Leadership</p>
          <h2 className="text-display-sm lg:text-display-md text-navy-900">Meet the CS Faculty</h2>
          <p className="mt-3 text-navy-400 max-w-2xl mx-auto">
            Guided by experienced educators and researchers driving innovation in Computer Science education at GGCB.
          </p>
        </AnimatedSection>

        <FacultyCarousel faculty={faculty} />
      </div>
    </section>
  )
}

/* ─────────────────────────── Student Reviews Carousel ─────────────────────────── */
function StudentReviewsCarousel({ reviews }) {
  const [current, setCurrent] = useState(0)
  const [isPaused, setIsPaused] = useState(false)
  const timerRef = useRef(null)
  const maxIndex = Math.max(0, reviews.length - 3)
  const CARD_W = 350
  const GAP = 24
  const STEP = CARD_W + GAP

  const go = (dir) => {
    setCurrent((prev) => {
      const next = prev + dir
      if (next < 0) return maxIndex
      if (next > maxIndex) return 0
      return next
    })
  }

  useEffect(() => {
    if (isPaused) return
    timerRef.current = setInterval(() => go(1), 4000)
    return () => clearInterval(timerRef.current)
  }, [isPaused])

  return (
    <div
      className="relative mx-auto"
      style={{ maxWidth: '1100px', height: '320px' }}
      onMouseEnter={() => setIsPaused(true)}
      onMouseLeave={() => setIsPaused(false)}
    >
      {/* Track */}
      <div className="overflow-hidden h-full">
        <div
          className="flex h-full"
          style={{
            gap: `${GAP}px`,
            transform: `translateX(-${current * STEP}px)`,
            transition: 'transform 0.7s cubic-bezier(0.4, 0, 0.2, 1)',
          }}
        >
          {reviews.map((r, i) => (
            <div key={i} className="shrink-0 flex flex-col bg-white rounded-2xl border border-surface-200 p-6 shadow-card hover:-translate-y-1 hover:shadow-elevated hover:border-accent-200 transition-all duration-300" style={{ width: `${CARD_W}px` }}>
              {/* Stars */}
              <div className="flex gap-0.5 mb-4">
                {Array.from({ length: 5 }).map((_, si) => (
                  <Star key={si} className={`w-4 h-4 ${si < r.rating ? 'text-accent-400 fill-accent-400' : 'text-navy-200'}`} />
                ))}
              </div>
              {/* Quote */}
              <p className="text-sm text-navy-600 leading-relaxed mb-5 flex-1">&ldquo;{r.text}&rdquo;</p>
              {/* Author */}
              <div className="flex items-center gap-3 pt-4 border-t border-surface-100">
                <span className="w-10 h-10 rounded-full bg-gradient-to-br from-accent-400 to-accent-600 flex items-center justify-center text-xs font-bold text-white shrink-0">
                  {r.avatar}
                </span>
                <div className="min-w-0">
                  <p className="text-sm font-bold text-navy-900 truncate">{r.name}</p>
                  <p className="text-xs text-navy-400">{r.semester}</p>
                </div>
              </div>
            </div>
          ))}
        </div>
      </div>

      {/* Left Arrow */}
      <button onClick={() => go(-1)} aria-label="Previous review" className="absolute left-0 top-1/2 -translate-y-1/2 -translate-x-10 z-20 w-10 h-10 rounded-full bg-white/90 border border-surface-200 shadow-md flex items-center justify-center hover:bg-white hover:shadow-lg transition-all cursor-pointer">
        <ChevronLeft className="w-5 h-5 text-navy-600" />
      </button>

      {/* Right Arrow */}
      <button onClick={() => go(1)} aria-label="Next review" className="absolute right-0 top-1/2 -translate-y-1/2 translate-x-10 z-20 w-10 h-10 rounded-full bg-white/90 border border-surface-200 shadow-md flex items-center justify-center hover:bg-white hover:shadow-lg transition-all cursor-pointer">
        <ChevronRight className="w-5 h-5 text-navy-600" />
      </button>
    </div>
  )
}

function StudentReviews() {
  // Static sample reviews — the /reviews/public endpoint is not part of this project's backend
  const reviews = [
    { name: 'Ali Hassan', semester: 'BS CS — 4th Semester', avatar: 'AH', rating: 5, text: 'Our database quiz came from a 40-question bank and everyone got a different set. Sharing answers is basically impossible now.' },
    { name: 'Fatima Zahra', semester: 'BS CS — 6th Semester', avatar: 'FZ', rating: 5, text: 'Results appeared the second I submitted. No waiting days to know how I did or which question I got wrong.' },
    { name: 'Qasim Ali', semester: 'BS CS — 2nd Semester', avatar: 'QA', rating: 4, text: 'Uploading the DOCX question bank took seconds. Not a single question had to be retyped.' },
    { name: 'Ayesha Bibi', semester: 'ICS — 1st Semester', avatar: 'AB', rating: 5, text: 'I attempt quizzes from my phone between classes. The question count and shuffle notice tell me exactly what to expect.' },
    { name: 'Hassan Raza', semester: 'BS CS — 5th Semester', avatar: 'HR', rating: 4, text: 'The answer review after submitting shows exactly which option was correct and what I picked.' },
    { name: 'Zainab Fatima', semester: 'BS CS — 3rd Semester', avatar: 'ZF', rating: 5, text: 'OTP signup took under a minute and my courses showed up based on my semester automatically.' },
  ]

  return (
    <section className="py-20 lg:py-28 bg-surface-50">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <AnimatedSection className="text-center mb-16">
          <p className="inline-flex items-center gap-2 px-4 py-1.5 rounded-full border border-accent-200 bg-accent-50 text-accent-600 text-xs font-bold uppercase tracking-widest mb-3">Student Voices</p>
          <h2 className="text-display-sm lg:text-display-md text-navy-900">What Students Say</h2>
          <p className="mt-3 text-navy-400 max-w-2xl mx-auto">
            Hear from CS students at GGCB who are already taking quizzes on the platform every day.
          </p>
        </AnimatedSection>

        <StudentReviewsCarousel reviews={reviews} />
      </div>
    </section>
  )
}

/* ─────────────────────────── FAQ ─────────────────────────── */
function FAQ() {
  const [openIndex, setOpenIndex] = useState(null)

  const faqs = [
    { question: 'How do I create an account and sign in?', answer: 'Students register with their official email address. After registering, a 6-digit OTP is sent to your email to verify your account. Once verified, you can sign in securely with your email and password.' },
    { question: 'What can I do with my student dashboard?', answer: 'Students see every quiz published to their courses, attempt their own shuffled subset of questions, and review their score with the full answer key right after submitting.' },
    { question: 'How do teachers create a quiz?', answer: 'Teachers pick a course, then either drop a DOCX, CSV or XLSX question bank — QuizLab parses every question and answer key — or write the questions by hand. They set how many questions each student receives, a deadline, and an optional time limit.' },
    { question: 'How does shuffling work?', answer: 'When a student opens a quiz, QuizLab randomly selects the configured number of questions from the bank and presents them in a random order. No two students receive the same set in the same order.' },
    { question: 'How is grading done?', answer: 'Submissions are graded automatically the moment they come in. Students instantly see their score, the questions they missed, and the correct answers. Teachers can expand any quiz to see every attempt and score.' },
    { question: "I forgot my password. What should I do?", answer: 'Use the "Forgot Password" option on the sign-in page. Enter your registered email address, and an OTP will be sent to you. Use it to reset your password and sign back in.' },
    { question: 'Which question formats are supported?', answer: 'CSV and XLSX files with columns Question, Option A–D and Answer, and DOCX files with numbered questions and a-b-c-d options. The Answer column accepts a letter, a number, or the option text.' },
    { question: 'How is my data protected?', answer: 'Your data is encrypted and stored securely, and OTP-based account verification ensures only verified users can access the system. Role-based permissions mean users only see what is relevant to them.' },
  ]

  return (
    <section id="faq" className="py-20 lg:py-28 bg-surface-0">
      <div className="max-w-3xl mx-auto px-4 sm:px-6 lg:px-8">
        <AnimatedSection className="text-center mb-16">
          <p className="inline-flex items-center gap-2 px-4 py-1.5 rounded-full border border-accent-200 bg-accent-50 text-accent-600 text-xs font-bold uppercase tracking-widest mb-3">Got Questions?</p>
          <h2 className="text-display-sm lg:text-display-md text-navy-900">Frequently Asked Questions</h2>
          <p className="mt-3 text-navy-400">Everything you need to know about getting started with QuizLab.</p>
        </AnimatedSection>

        <StaggerContainer className="space-y-3">
          {faqs.map((faq, i) => (
            <div key={i} className="stagger-child card overflow-hidden transition-all duration-200">
              <button onClick={() => setOpenIndex(openIndex === i ? null : i)} className="w-full flex items-center justify-between p-5 text-left group hover:bg-surface-50 transition-colors rounded-2xl">
                <span className="text-sm font-semibold text-navy-900 pr-4 group-hover:text-navy-900">{faq.question}</span>
                {openIndex === i ? <ChevronUp className="w-5 h-5 text-accent-500 shrink-0" /> : <ChevronDown className="w-5 h-5 text-navy-400 shrink-0 group-hover:text-navy-600" />}
              </button>
              {openIndex === i && (
                <div className="px-5 pb-5 border-t border-surface-100">
                  <p className="text-sm text-navy-400 leading-relaxed pt-4">{faq.answer}</p>
                </div>
              )}
            </div>
          ))}
        </StaggerContainer>
      </div>
    </section>
  )
}

/* ──────────────────────────── CTA ──────────────────────────── */
function CTA() {
  return (
    <section className="py-20 lg:py-28 bg-navy-950 relative overflow-hidden">
      {/* Background image */}
      <div className="absolute inset-0">
        <img
          src="/cta bg image.jfif"
          alt="Govt. Graduate College Burewala"
          className="w-full h-full object-cover object-center opacity-40"
          loading="lazy"
        />
        <div className="absolute inset-0 bg-navy-950/80" />
      </div>
      <div
        className="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 w-[600px] h-[600px] rounded-full opacity-[0.06]"
        style={{ background: 'radial-gradient(circle, #fbbf24 0%, transparent 65%)' }}
      />

      <AnimatedSection className="relative max-w-3xl mx-auto px-4 sm:px-6 lg:px-8 text-center">
        <h2 className="text-display-sm lg:text-display-md text-white font-extrabold">Ready to Take Your First Quiz?</h2>
        <p className="mt-4 text-white/50 text-lg max-w-xl mx-auto">
          Join the CS students and faculty already quizzing on QuizLab. Registration takes less than 60 seconds — verify with an email code and your courses appear automatically.
        </p>
        <div className="mt-10 flex justify-center gap-3 sm:gap-4">
          <Link
            to="/register"
            className="inline-flex items-center justify-center gap-2 flex-1 sm:flex-none px-6 sm:px-8 py-3.5 rounded-xl text-sm sm:text-base font-bold bg-accent-500 text-black hover:bg-accent-400 transition-colors shadow-lg shadow-accent-500/20"
          >
            Create Free Account
            <ArrowRight className="w-4 h-4 sm:w-5 sm:h-5 shrink-0" />
          </Link>
          <Link to="/login" className="inline-flex items-center justify-center gap-2 px-4 sm:px-8 py-2.5 sm:py-3.5 rounded-xl text-xs sm:text-base font-semibold text-white border border-white/15 hover:bg-white/5 transition-colors whitespace-nowrap">
            Sign In
          </Link>
        </div>
      </AnimatedSection>
    </section>
  )
}

/* ──────────────────────────── Footer ──────────────────────────── */
function Footer() {
  return (
    <footer className="bg-navy-950 border-t border-white/5">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <AnimatedSection className="py-8 sm:py-16 grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-6 sm:gap-10 lg:gap-8">
          <div className="lg:col-span-1">
            <div className="flex items-center gap-3 mb-3">
              <img src="/college-logo.png" alt="GGCB Logo" className="w-8 h-8 rounded-lg object-cover" />
              <div>
                <p className="text-sm font-bold text-white">QuizLab</p>
                <p className="text-xs text-white/40">Govt. Graduate College Burewala</p>
              </div>
            </div>
            <p className="text-xs sm:text-sm text-white/40 leading-relaxed">
              The CS Department's quiz platform at Govt. Graduate College Burewala. Upload a question bank, shuffle it per student, grade it instantly.
            </p>
            <div className="flex gap-2 sm:gap-3 mt-3">
              {[{ icon: Facebook, label: 'Facebook' }, { icon: Instagram, label: 'Instagram' }, { icon: Twitter, label: 'Twitter' }, { icon: Youtube, label: 'YouTube' }].map((s) => (
                <a key={s.label} href="#" aria-label={s.label} className="w-8 h-8 sm:w-9 sm:h-9 rounded-lg bg-white/5 hover:bg-accent-500/20 flex items-center justify-center text-white/30 hover:text-accent-400 transition-colors">
                  <s.icon className="w-3.5 h-3.5 sm:w-4 sm:h-4" />
                </a>
              ))}
            </div>
          </div>

          <div>
            <h3 className="text-xs font-bold text-white/30 uppercase tracking-wider mb-3 sm:mb-5">Quick Links</h3>
            <ul className="space-y-2 sm:space-y-3">
              {[
                { label: 'Home', href: '#hero' },
                { label: 'Features', href: '#solution' },
                { label: 'How It Works', href: '#how-it-works' },
                { label: 'Faculty', href: '#faculty' },
                { label: 'FAQ', href: '#faq' },
              ].map((link) => (
                <li key={link.label}><a href={link.href} className="text-xs sm:text-sm text-white/40 hover:text-accent-400 transition-colors">{link.label}</a></li>
              ))}
            </ul>
          </div>

          <div>
            <h3 className="text-xs font-bold text-white/30 uppercase tracking-wider mb-3 sm:mb-5">QuizLab</h3>
            <ul className="space-y-2 sm:space-y-3">
              {[
                { label: 'Student Portal', href: '/student' },
                { label: 'Teacher Portal', href: '/teacher' },
                { label: 'Admin Dashboard', href: '/admin' },
                { label: 'Sign In', href: '/login' },
                { label: 'Create Account', href: '/register' },
              ].map((link) => (
                <li key={link.label}><Link to={link.href} className="text-xs sm:text-sm text-white/40 hover:text-accent-400 transition-colors">{link.label}</Link></li>
              ))}
            </ul>
          </div>

          <div>
            <h3 className="text-xs font-bold text-white/30 uppercase tracking-wider mb-3 sm:mb-5">Contact Us</h3>
            <ul className="space-y-3 sm:space-y-4">
              <li className="flex items-start gap-2.5 sm:gap-3">
                <MapPin className="w-3.5 h-3.5 sm:w-4 sm:h-4 text-accent-500 mt-0.5 shrink-0" />
                <span className="text-xs sm:text-sm text-white/40 leading-relaxed">CS Dept., Govt. Graduate College Burewala,<br />Vehari District, Punjab, Pakistan</span>
              </li>
              <li className="flex items-center gap-2.5 sm:gap-3">
                <Phone className="w-3.5 h-3.5 sm:w-4 sm:h-4 text-accent-500 shrink-0" />
                <span className="text-xs sm:text-sm text-white/40">+92 67 334 5678</span>
              </li>
              <li className="flex items-center gap-2.5 sm:gap-3">
                <Mail className="w-3.5 h-3.5 sm:w-4 sm:h-4 text-accent-500 shrink-0" />
                <span className="text-xs sm:text-sm text-white/40">cs@ggcb.edu.pk</span>
              </li>
            </ul>
          </div>
        </AnimatedSection>

        <div className="py-4 sm:py-6 border-t border-white/5 flex flex-col sm:flex-row items-center justify-between gap-3 sm:gap-4">
          <p className="text-[10px] sm:text-xs text-white/25">© {new Date().getFullYear()} Govt. Graduate College Burewala. All rights reserved.</p>
          <div className="flex gap-4 sm:gap-6">
            <a href="#" className="text-[10px] sm:text-xs text-white/25 hover:text-white/50 transition-colors">Privacy Policy</a>
            <a href="#" className="text-[10px] sm:text-xs text-white/25 hover:text-white/50 transition-colors">Terms of Service</a>
          </div>
        </div>
      </div>
    </footer>
  )
}

/* ─────────────────────── Exported Landing Page ─────────────────────── */
export default function LandingPage() {
  return (
    <div className="min-h-screen">
      <Navbar />
      <Hero />
      <SocialProof />
      <ProblemStatement />
      <Solution />
      <Faculty />
      <HowItWorks />
      <StudentReviews />
      <FAQ />
      <CTA />
      <Footer />
    </div>
  )
}
