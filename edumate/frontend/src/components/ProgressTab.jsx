import { useState, useEffect } from 'react'
import { fetchProgress } from '../utils/api'
import {
  BarChart3, Loader2, RefreshCcw, AlertTriangle
} from 'lucide-react'
import {
  BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, Cell
} from 'recharts'

const STATUS_COLORS = {
  'Strong': '#4cc38a',
  'Needs revision': '#d4956a',
  'Weak topic': '#e5484d',
}

export default function ProgressTab({ studentId }) {
  const [progress, setProgress] = useState(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState(null)

  const loadProgress = async () => {
    setLoading(true)
    setError(null)
    try {
      const data = await fetchProgress(studentId)
      setProgress(data)
    } catch (e) {
      setError(e.message)
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    loadProgress()
  }, [studentId])

  if (loading) {
    return (
      <div className="flex flex-col items-center justify-center py-24 space-y-3">
        <Loader2 size={20} className="animate-spin text-accent" />
        <p className="text-xs text-gray-400 font-mono">Loading progress data...</p>
      </div>
    )
  }

  if (error) {
    return (
      <div className="max-w-2xl mx-auto space-y-3">
        <div className="flex items-center gap-2 bg-dark-800 border border-negative/30 text-negative text-xs p-4 rounded-lg">
          <AlertTriangle size={15} className="shrink-0" />
          <span>{error}</span>
        </div>
        <button
          onClick={loadProgress}
          className="flex items-center gap-1.5 bg-dark-750 hover:bg-dark-700 text-gray-200 text-xs px-3.5 py-1.5 rounded-md border border-white/[0.08] transition-colors"
        >
          <RefreshCcw size={12} />
          <span>Retry</span>
        </button>
      </div>
    )
  }

  if (!progress) return null

  const chartData = progress.topics.map(t => ({
    name: t.topic.length > 18 ? t.topic.slice(0, 18) + '...' : t.topic,
    fullName: t.topic,
    mastery: t.mastery_percentage,
    status: t.status,
  }))

  return (
    <div className="max-w-3xl mx-auto space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between pb-1">
        <div className="flex items-center gap-2">
          <BarChart3 size={16} className="text-gray-400" />
          <h2 className="text-sm font-medium text-gray-200">Topic mastery</h2>
        </div>
        <button
          onClick={loadProgress}
          className="flex items-center gap-1.5 text-xs bg-dark-800 hover:bg-dark-750 text-gray-300 px-3 py-1.5 rounded-md border border-white/[0.08] transition-colors"
        >
          <RefreshCcw size={12} />
          <span>Refresh</span>
        </button>
      </div>

      {/* Numbers-First Stat Row */}
      <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
        <div className="bg-dark-800 border border-white/[0.08] rounded-lg p-4 space-y-1">
          <p className="text-[12px] text-gray-400">Overall mastery</p>
          <p className="text-2xl font-medium text-gray-100 tabular-nums">
            {progress.overall_mastery.toFixed(0)}%
          </p>
        </div>
        <div className="bg-dark-800 border border-white/[0.08] rounded-lg p-4 space-y-1">
          <p className="text-[12px] text-gray-400">Quizzes taken</p>
          <p className="text-2xl font-medium text-gray-100 tabular-nums">
            {progress.total_quizzes_taken}
          </p>
        </div>
        <div className="bg-dark-800 border border-white/[0.08] rounded-lg p-4 space-y-1">
          <p className="text-[12px] text-gray-400">Questions answered</p>
          <p className="text-2xl font-medium text-gray-100 tabular-nums">
            {progress.total_questions_attempted}
          </p>
        </div>
        <div className="bg-dark-800 border border-white/[0.08] rounded-lg p-4 space-y-1">
          <p className="text-[12px] text-gray-400">Topics covered</p>
          <p className="text-2xl font-medium text-gray-100 tabular-nums">
            {progress.topics.length}
          </p>
        </div>
      </div>

      {/* Mastery Chart (The Moment) */}
      {chartData.length > 0 && (
        <div className="bg-dark-800 border border-white/[0.08] rounded-xl p-5 space-y-4">
          <div className="flex items-center justify-between">
            <h3 className="text-xs font-medium text-gray-200">Mastery by topic</h3>
            <span className="text-[11px] text-gray-500 font-mono">Percentage score</span>
          </div>

          <ResponsiveContainer width="100%" height={Math.max(180, chartData.length * 40)}>
            <BarChart data={chartData} layout="vertical" margin={{ left: 10, right: 20, top: 4, bottom: 4 }}>
              <CartesianGrid strokeDasharray="2 2" stroke="rgba(255, 255, 255, 0.05)" horizontal={false} />
              <XAxis type="number" domain={[0, 100]} tick={{ fill: '#85858b', fontSize: 11 }} />
              <YAxis type="category" dataKey="name" width={130} tick={{ fill: '#a1a1a6', fontSize: 11 }} />
              <Tooltip
                cursor={{ fill: 'rgba(255, 255, 255, 0.02)' }}
                contentStyle={{
                  background: '#19191b',
                  border: '1px solid rgba(255, 255, 255, 0.08)',
                  borderRadius: '6px',
                  fontSize: '12px',
                  color: '#ededed',
                  padding: '6px 10px',
                }}
                formatter={(value, name, props) => [`${value.toFixed(0)}%`, props.payload.fullName]}
              />
              <Bar dataKey="mastery" radius={[0, 4, 4, 0]} barSize={16}>
                {chartData.map((entry, idx) => {
                  const isTop = entry.mastery === Math.max(...chartData.map(c => c.mastery))
                  return (
                    <Cell
                      key={idx}
                      fill={isTop ? '#d4956a' : (STATUS_COLORS[entry.status] || '#a1a1a6')}
                      opacity={isTop ? 1 : 0.8}
                    />
                  )
                })}
              </Bar>
            </BarChart>
          </ResponsiveContainer>
        </div>
      )}

      {/* Topics Detailed Table */}
      {progress.topics.length > 0 && (
        <div className="bg-dark-800 border border-white/[0.08] rounded-xl overflow-hidden">
          <div className="overflow-x-auto">
            <table className="w-full text-xs">
              <thead>
                <tr className="border-b border-white/[0.06] bg-dark-850">
                  <th className="text-left px-4 py-2.5 text-gray-400 font-medium">Topic</th>
                  <th className="text-center px-4 py-2.5 text-gray-400 font-medium">Attempts</th>
                  <th className="text-center px-4 py-2.5 text-gray-400 font-medium">Correct</th>
                  <th className="text-center px-4 py-2.5 text-gray-400 font-medium">Mastery</th>
                  <th className="text-right px-4 py-2.5 text-gray-400 font-medium">Status</th>
                </tr>
              </thead>
              <tbody>
                {progress.topics.map((t, i) => (
                  <tr key={i} className="border-b border-white/[0.04] hover:bg-dark-750 transition-colors">
                    <td className="px-4 py-2.5 text-gray-200 font-medium">{t.topic}</td>
                    <td className="text-center px-4 py-2.5 text-gray-400 font-mono">{t.total_attempts}</td>
                    <td className="text-center px-4 py-2.5 text-gray-400 font-mono">{t.correct_attempts}</td>
                    <td className="text-center px-4 py-2.5">
                      <div className="flex items-center justify-center gap-2">
                        <div className="w-16 h-1 bg-dark-900 rounded-full overflow-hidden">
                          <div
                            className="h-full rounded-full"
                            style={{
                              width: `${t.mastery_percentage}%`,
                              background: STATUS_COLORS[t.status] || '#a1a1a6',
                            }}
                          />
                        </div>
                        <span className="text-gray-300 font-mono text-[11px] w-7 text-right">
                          {t.mastery_percentage.toFixed(0)}%
                        </span>
                      </div>
                    </td>
                    <td className="text-right px-4 py-2.5">
                      <span
                        className="text-[11px] px-2 py-0.5 rounded font-medium"
                        style={{
                          color: STATUS_COLORS[t.status] || '#a1a1a6',
                          background: 'rgba(255, 255, 255, 0.04)',
                        }}
                      >
                        {t.status}
                      </span>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {/* Recommended Topics For Revision */}
      {progress.recommended_revision_topics.length > 0 && (
        <div className="bg-dark-800 border border-white/[0.08] rounded-xl p-4 space-y-2">
          <h3 className="text-xs font-medium text-gray-300">
            Recommended revision
          </h3>
          <div className="flex flex-wrap gap-1.5">
            {progress.recommended_revision_topics.map((topic, i) => (
              <span
                key={i}
                className="bg-dark-900 text-gray-300 text-xs px-2.5 py-1 rounded-md border border-white/[0.06] font-mono text-[11px]"
              >
                {topic}
              </span>
            ))}
          </div>
        </div>
      )}

      {progress.topics.length === 0 && (
        <div className="text-center py-16 bg-dark-800 border border-white/[0.08] rounded-xl">
          <p className="text-gray-400 text-xs">No quiz attempts recorded yet.</p>
          <p className="text-gray-500 text-[11px] mt-1">Take a practice quiz to generate topic mastery analytics.</p>
        </div>
      )}
    </div>
  )
}
