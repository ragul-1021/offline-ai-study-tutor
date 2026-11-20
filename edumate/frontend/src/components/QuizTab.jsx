import { useState } from 'react'
import { generateQuiz, submitAnswer } from '../utils/api'
import {
  Brain, Loader2, CheckCircle2, XCircle, AlertTriangle,
  Hash, ChevronRight
} from 'lucide-react'

const DIFFICULTIES = ['easy', 'medium', 'hard']

export default function QuizTab({ studentId, documents }) {
  const [topic, setTopic] = useState('')
  const [difficulty, setDifficulty] = useState('medium')
  const [numQuestions, setNumQuestions] = useState(5)
  const [selectedDocIds, setSelectedDocIds] = useState([])
  const [generating, setGenerating] = useState(false)
  const [quiz, setQuiz] = useState(null)
  const [answers, setAnswers] = useState({})
  const [results, setResults] = useState({})
  const [submitting, setSubmitting] = useState({})
  const [error, setError] = useState(null)

  const handleGenerate = async () => {
    if (selectedDocIds.length === 0) {
      setError('Please select at least one document')
      return
    }
    setError(null)
    setGenerating(true)
    setQuiz(null)
    setAnswers({})
    setResults({})
    try {
      const data = await generateQuiz({
        documentIds: selectedDocIds,
        topic: topic || 'General',
        difficulty,
        numberOfQuestions: numQuestions,
        studentId,
      })
      setQuiz(data)
    } catch (e) {
      setError(e.message)
    } finally {
      setGenerating(false)
    }
  }

  const handleSubmitAnswer = async (questionId) => {
    const ans = answers[questionId]
    if (!ans?.trim()) return
    setSubmitting(prev => ({ ...prev, [questionId]: true }))
    try {
      const result = await submitAnswer({
        questionId,
        studentAnswer: ans,
        studentId,
      })
      setResults(prev => ({ ...prev, [questionId]: result }))
    } catch (e) {
      setResults(prev => ({ ...prev, [questionId]: { error: e.message } }))
    } finally {
      setSubmitting(prev => ({ ...prev, [questionId]: false }))
    }
  }

  const totalSubmitted = Object.keys(results).length
  const totalCorrect = Object.values(results).filter(r => r.is_correct).length

  return (
    <div className="max-w-3xl mx-auto space-y-6">
      {/* Quiz Configuration Surface */}
      <div className="bg-dark-800 border border-white/[0.08] rounded-xl p-5 space-y-5">
        <div className="flex items-center justify-between pb-3 border-b border-white/[0.06]">
          <div className="flex items-center gap-2">
            <Brain size={16} className="text-gray-400" />
            <h2 className="text-sm font-medium text-gray-200">Practice quiz</h2>
          </div>
          <span className="text-xs text-gray-500 font-mono">
            Generated from indexed notes
          </span>
        </div>

        <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
          <div>
            <label className="text-xs text-gray-400 mb-1.5 block">Topic</label>
            <input
              value={topic}
              onChange={e => setTopic(e.target.value)}
              placeholder="e.g. Current Electricity"
              className="w-full bg-dark-900 border border-white/[0.08] rounded-md px-3 py-1.5 text-xs text-gray-100 placeholder-gray-500 focus:outline-none focus:border-white/20 transition-colors"
            />
          </div>

          <div>
            <label className="text-xs text-gray-400 mb-1.5 block">Difficulty</label>
            <div className="flex bg-dark-900 p-0.5 rounded-md border border-white/[0.06]">
              {DIFFICULTIES.map(d => (
                <button
                  key={d}
                  onClick={() => setDifficulty(d)}
                  className={`flex-1 py-1 rounded text-xs font-medium capitalize transition-colors ${
                    difficulty === d
                      ? 'bg-dark-750 text-gray-100 border border-white/[0.08]'
                      : 'text-gray-400 hover:text-gray-200'
                  }`}
                >
                  {d}
                </button>
              ))}
            </div>
          </div>

          <div>
            <label className="text-xs text-gray-400 mb-1.5 block">Questions</label>
            <input
              type="number"
              min={1}
              max={15}
              value={numQuestions}
              onChange={e => setNumQuestions(parseInt(e.target.value) || 5)}
              className="w-full bg-dark-900 border border-white/[0.08] rounded-md px-3 py-1.5 text-xs text-gray-100 font-mono focus:outline-none focus:border-white/20 transition-colors"
            />
          </div>
        </div>

        {/* Source Documents */}
        <div className="space-y-1.5">
          <label className="text-xs text-gray-400 block">Select notes to test on</label>
          <div className="flex flex-wrap gap-1.5 pt-0.5">
            {documents.length === 0 ? (
              <p className="text-xs text-gray-500 italic py-1">Upload study PDFs in sidebar first.</p>
            ) : (
              documents.map(doc => {
                const isChecked = selectedDocIds.includes(doc.document_id)
                return (
                  <button
                    key={doc.document_id}
                    onClick={() => {
                      setSelectedDocIds(prev =>
                        prev.includes(doc.document_id)
                          ? prev.filter(id => id !== doc.document_id)
                          : [...prev, doc.document_id]
                      )
                    }}
                    className={`flex items-center gap-1.5 px-2.5 py-1 rounded-md text-xs transition-colors border ${
                      isChecked
                        ? 'bg-dark-700 border-accent/40 text-gray-100'
                        : 'bg-dark-900 border-white/[0.06] text-gray-400 hover:text-gray-200'
                    }`}
                  >
                    <Hash size={11} className="text-gray-400" />
                    <span>{doc.document_name.slice(0, 24)}</span>
                  </button>
                )
              })
            )}
          </div>
        </div>

        <button
          onClick={handleGenerate}
          disabled={generating || selectedDocIds.length === 0}
          className="w-full flex items-center justify-center gap-2 bg-gray-100 hover:bg-white text-dark-950 font-medium py-2 rounded-md transition-colors text-xs disabled:opacity-40 disabled:hover:bg-gray-100 cursor-pointer shadow-sm"
        >
          {generating ? <Loader2 size={14} className="animate-spin text-dark-950" /> : null}
          <span>{generating ? 'Formulating quiz with Gemma...' : 'Generate quiz'}</span>
        </button>

        {error && (
          <div className="flex items-center gap-2 bg-dark-900 border border-negative/30 text-negative text-xs p-3 rounded-md">
            <AlertTriangle size={14} className="shrink-0" />
            <span>{error}</span>
          </div>
        )}
      </div>

      {/* Quiz Questions List */}
      {quiz && (
        <div className="space-y-4">
          <div className="flex items-center justify-between px-1">
            <h3 className="text-xs font-medium text-gray-300">
              Quiz: {quiz.topic} ({quiz.difficulty}) · {quiz.questions.length} questions
            </h3>
            {totalSubmitted > 0 && (
              <span className="text-xs font-mono text-gray-300 bg-dark-800 border border-white/[0.08] px-2.5 py-0.5 rounded">
                Score: {totalCorrect} / {totalSubmitted} ({((totalCorrect / totalSubmitted) * 100).toFixed(0)}%)
              </span>
            )}
          </div>

          {quiz.questions.map((q, idx) => {
            const result = results[q.question_id]
            const isSubmitting = submitting[q.question_id]
            const answered = !!result

            return (
              <div
                key={q.question_id}
                className="bg-dark-800 border border-white/[0.08] rounded-xl p-5 space-y-4"
              >
                <div className="flex items-start gap-3">
                  <span className="bg-dark-750 border border-white/[0.06] text-gray-300 text-xs font-mono w-6 h-6 flex items-center justify-center rounded shrink-0">
                    {idx + 1}
                  </span>
                  <div className="space-y-1 flex-1">
                    <p className="text-sm font-medium text-gray-100 leading-snug">{q.question_text}</p>
                    <span className="text-[11px] text-gray-500 uppercase font-mono tracking-wide">{q.question_type}</span>
                  </div>
                </div>

                {/* Multiple Choice Options */}
                {q.question_type === 'mcq' && q.options && (
                  <div className="space-y-1.5 pl-9">
                    {q.options.map((opt, optIdx) => {
                      const letter = String.fromCharCode(65 + optIdx)
                      const selected = answers[q.question_id] === letter
                      return (
                        <button
                          key={optIdx}
                          onClick={() => !answered && setAnswers(prev => ({ ...prev, [q.question_id]: letter }))}
                          disabled={answered}
                          className={`w-full text-left flex items-center gap-2.5 px-3 py-2 rounded-md text-xs border transition-colors ${
                            selected
                              ? 'bg-dark-750 border-white/20 text-gray-100'
                              : 'bg-dark-900 border-white/[0.06] text-gray-300 hover:border-white/[0.12] disabled:hover:border-white/[0.06]'
                          }`}
                        >
                          <span className="font-mono text-gray-400 text-xs w-4">{letter}.</span>
                          <span className="flex-1">{opt}</span>
                        </button>
                      )
                    })}
                  </div>
                )}

                {/* Short Answer Input */}
                {q.question_type !== 'mcq' && !answered && (
                  <div className="pl-9">
                    <textarea
                      value={answers[q.question_id] || ''}
                      onChange={e => setAnswers(prev => ({ ...prev, [q.question_id]: e.target.value }))}
                      placeholder="Type your answer..."
                      rows={2}
                      className="w-full bg-dark-900 border border-white/[0.08] rounded-md px-3 py-2 text-xs text-gray-100 placeholder-gray-500 focus:outline-none focus:border-white/20 transition-colors resize-none"
                    />
                  </div>
                )}

                {/* Submit Action */}
                {!answered && (
                  <div className="pl-9">
                    <button
                      onClick={() => handleSubmitAnswer(q.question_id)}
                      disabled={!answers[q.question_id]?.trim() || isSubmitting}
                      className="flex items-center gap-1.5 bg-dark-750 hover:bg-dark-700 text-gray-200 text-xs font-medium px-3.5 py-1.5 rounded-md border border-white/[0.08] transition-colors disabled:opacity-40"
                    >
                      {isSubmitting ? <Loader2 size={12} className="animate-spin text-accent" /> : <ChevronRight size={12} />}
                      <span>Submit answer</span>
                    </button>
                  </div>
                )}

                {/* Evaluation Feedback */}
                {answered && !result.error && (
                  <div className={`ml-9 p-3 rounded-md text-xs border ${
                    result.is_correct
                      ? 'bg-dark-900 border-positive/30 text-positive'
                      : 'bg-dark-900 border-negative/30 text-negative'
                  }`}>
                    <div className="flex items-center gap-2 mb-1">
                      {result.is_correct
                        ? <CheckCircle2 size={14} className="shrink-0" />
                        : <XCircle size={14} className="shrink-0" />}
                      <span className="font-medium">
                        {result.is_correct ? 'Correct' : 'Needs review'} · Score: {(result.score * 100).toFixed(0)}%
                      </span>
                    </div>
                    <p className="text-gray-300 leading-relaxed text-xs">{result.feedback}</p>
                    {result.suggested_revision_topic && (
                      <p className="text-gray-400 mt-1 font-mono text-[11px]">
                        Review topic: {result.suggested_revision_topic}
                      </p>
                    )}
                  </div>
                )}

                {answered && result.error && (
                  <div className="ml-9 text-xs text-negative bg-dark-900 border border-negative/30 p-2.5 rounded-md">
                    Error evaluating: {result.error}
                  </div>
                )}
              </div>
            )
          })}
        </div>
      )}
    </div>
  )
}
