import { useState, useEffect } from 'react'
import { fetchDocuments, fetchHealth } from './utils/api'
import Sidebar from './components/Sidebar'
import StudyTab from './components/StudyTab'
import QuizTab from './components/QuizTab'
import ProgressTab from './components/ProgressTab'
import { BookOpen, Brain, BarChart3, PanelLeft, Wifi, WifiOff } from 'lucide-react'

const TABS = [
  { id: 'study', label: 'Study', icon: BookOpen },
  { id: 'quiz', label: 'Quiz', icon: Brain },
  { id: 'progress', label: 'Progress', icon: BarChart3 },
]

export default function App() {
  const [activeTab, setActiveTab] = useState('study')
  const [studentId, setStudentId] = useState('student_1')
  const [studentLevel, setStudentLevel] = useState('Class 12')
  const [documents, setDocuments] = useState([])
  const [backendOnline, setBackendOnline] = useState(false)
  const [sidebarOpen, setSidebarOpen] = useState(true)

  useEffect(() => {
    const check = async () => {
      try {
        await fetchHealth()
        setBackendOnline(true)
      } catch {
        setBackendOnline(false)
      }
    }
    check()
    const interval = setInterval(check, 30000)
    return () => clearInterval(interval)
  }, [])

  const loadDocuments = async () => {
    try {
      const docs = await fetchDocuments()
      setDocuments(docs)
    } catch (e) {
      console.error('Failed to load documents:', e)
    }
  }

  useEffect(() => {
    if (backendOnline) loadDocuments()
  }, [backendOnline])

  return (
    <div className="h-screen flex bg-dark-900 text-gray-100 overflow-hidden font-sans">
      {/* Sidebar */}
      <Sidebar
        open={sidebarOpen}
        onToggle={() => setSidebarOpen(!sidebarOpen)}
        studentId={studentId}
        setStudentId={setStudentId}
        studentLevel={studentLevel}
        setStudentLevel={setStudentLevel}
        documents={documents}
        onDocumentUploaded={loadDocuments}
      />

      {/* Main Content Area */}
      <div className="flex-1 flex flex-col min-w-0 bg-dark-850">
        {/* Top Header */}
        <header className="h-14 border-b border-white/[0.08] px-6 flex items-center justify-between shrink-0 bg-dark-900">
          <div className="flex items-center gap-3">
            {!sidebarOpen && (
              <button
                onClick={() => setSidebarOpen(true)}
                title="Open sidebar"
                className="p-1.5 text-gray-400 hover:text-gray-200 hover:bg-dark-750 rounded-md transition-colors"
              >
                <PanelLeft size={16} />
              </button>
            )}
            <div className="flex items-center gap-2.5">
              <span className="font-semibold text-base text-gray-100 tracking-tight">
                EduMate
              </span>
              <span className="text-xs text-gray-400 border border-white/[0.08] px-2 py-0.5 rounded">
                Offline AI Tutor
              </span>
            </div>
          </div>

          <div className="flex items-center gap-4">
            {/* Tabs */}
            <nav className="flex bg-dark-800 p-0.5 rounded-lg border border-white/[0.06]">
              {TABS.map(tab => {
                const Icon = tab.icon
                const isActive = activeTab === tab.id
                return (
                  <button
                    key={tab.id}
                    onClick={() => setActiveTab(tab.id)}
                    className={`flex items-center gap-1.5 px-3 py-1.5 rounded-md text-xs font-medium transition-colors ${
                      isActive
                        ? 'bg-dark-700 text-gray-100 shadow-sm border border-white/[0.08]'
                        : 'text-gray-400 hover:text-gray-200'
                    }`}
                  >
                    <Icon size={14} className={isActive ? 'text-accent' : 'text-gray-400'} />
                    <span>{tab.label}</span>
                  </button>
                )
              })}
            </nav>

            {/* Status indicator */}
            <div className="flex items-center gap-1.5 text-xs text-gray-400">
              <span
                className={`w-1.5 h-1.5 rounded-full ${
                  backendOnline ? 'bg-positive' : 'bg-negative'
                }`}
              />
              <span className="text-[12px]">{backendOnline ? 'Ready' : 'Offline'}</span>
            </div>
          </div>
        </header>

        {/* Tab Viewport */}
        <main className="flex-1 overflow-auto p-6 md:p-8">
          {activeTab === 'study' && (
            <StudyTab
              studentId={studentId}
              studentLevel={studentLevel}
              documents={documents}
            />
          )}
          {activeTab === 'quiz' && (
            <QuizTab
              studentId={studentId}
              documents={documents}
            />
          )}
          {activeTab === 'progress' && (
            <ProgressTab studentId={studentId} />
          )}
        </main>
      </div>
    </div>
  )
}
