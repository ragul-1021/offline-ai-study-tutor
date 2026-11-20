import { useState, useRef, useEffect, useCallback, Component } from 'react'
import ReactMarkdown from 'react-markdown'
import remarkGfm from 'remark-gfm'
import remarkMath from 'remark-math'
import rehypeKatex from 'rehype-katex'
import { chatStream } from '../utils/api'
import {
  Zap, BookOpen, Send, Loader2, Download, ChevronDown,
  Clock, Hash, AlertTriangle, RotateCcw, Copy, Check
} from 'lucide-react'

class MarkdownErrorBoundary extends Component {
  constructor(props) {
    super(props)
    this.state = { hasError: false }
  }
  static getDerivedStateFromError() {
    return { hasError: true }
  }
  componentDidCatch(error) {
    console.warn('Math streaming render notice:', error)
  }
  componentDidUpdate(prevProps) {
    if (prevProps.content !== this.props.content && this.state.hasError) {
      this.setState({ hasError: false })
    }
  }
  render() {
    if (this.state.hasError) {
      return <div className="whitespace-pre-wrap leading-relaxed text-gray-300 font-mono text-sm">{this.props.content}</div>
    }
    return this.props.children
  }
}

const MARKS_OPTIONS = [
  { value: null, label: 'Auto', desc: 'Balanced explanation' },
  { value: 2, label: '2 Marks', desc: '~50 words' },
  { value: 5, label: '5 Marks', desc: '~150 words' },
  { value: 10, label: '10 Marks', desc: '~300 words' },
  { value: 12, label: '12 Marks', desc: '~400 words' },
  { value: 16, label: '16 Marks', desc: '~550 words' },
]

export default function StudyTab({ studentId, studentLevel, documents }) {
  const [directMode, setDirectMode] = useState(true)
  const [targetMarks, setTargetMarks] = useState(null)
  const [selectedDocIds, setSelectedDocIds] = useState([])
  const [question, setQuestion] = useState('')
  const [answer, setAnswer] = useState('')
  const [sources, setSources] = useState([])
  const [fallback, setFallback] = useState(false)
  const [streaming, setStreaming] = useState(false)
  const [error, setError] = useState(null)
  const [startTime, setStartTime] = useState(null)
  const [elapsed, setElapsed] = useState(0)
  const [tokenCount, setTokenCount] = useState(0)
  const [copied, setCopied] = useState(false)
  const [showSources, setShowSources] = useState(false)
  const answerRef = useRef(null)
  const abortRef = useRef(null)
  const timerRef = useRef(null)

  // Auto-scroll to bottom during streaming
  useEffect(() => {
    if (streaming && answerRef.current) {
      const el = answerRef.current
      el.scrollTop = el.scrollHeight
    }
  }, [answer, streaming])

  // Timer for elapsed time
  useEffect(() => {
    if (streaming && startTime) {
      timerRef.current = setInterval(() => {
        setElapsed(Math.floor((Date.now() - startTime) / 1000))
      }, 500)
    }
    return () => clearInterval(timerRef.current)
  }, [streaming, startTime])

  const handleAsk = useCallback(async () => {
    if (!question.trim() || streaming) return

    setAnswer('')
    setSources([])
    setFallback(false)
    setError(null)
    setStreaming(true)
    setTokenCount(0)
    setStartTime(Date.now())
    setElapsed(0)
    setShowSources(false)
    setCopied(false)

    const controller = new AbortController()
    abortRef.current = controller

    try {
      const { body, sources: srcData, fallbackMode } = await chatStream(question, {
        studentLevel,
        documentIds: directMode ? null : (selectedDocIds.length > 0 ? selectedDocIds : null),
        directMode,
        targetMarks,
      })

      setSources(srcData)
      setFallback(fallbackMode)

      const reader = body.getReader()
      const decoder = new TextDecoder()
      let fullText = ''
      let tokens = 0

      while (true) {
        const { done, value } = await reader.read()
        if (done) break
        if (controller.signal.aborted) {
          reader.cancel()
          break
        }
        const chunk = decoder.decode(value, { stream: true })
        fullText += chunk
        tokens += chunk.split(/\s+/).filter(Boolean).length
        setAnswer(fullText)
        setTokenCount(tokens)
      }
    } catch (e) {
      if (e.name !== 'AbortError') {
        setError(e.message || 'Failed to get response')
      }
    } finally {
      setStreaming(false)
      clearInterval(timerRef.current)
      abortRef.current = null
    }
  }, [question, streaming, studentLevel, directMode, selectedDocIds, targetMarks])

  const handleStop = () => {
    abortRef.current?.abort()
    setStreaming(false)
  }

  const handleKeyDown = (e) => {
    if (e.key === 'Enter' && (e.ctrlKey || e.metaKey)) {
      handleAsk()
    }
  }

  const handleCopy = async () => {
    await navigator.clipboard.writeText(answer)
    setCopied(true)
    setTimeout(() => setCopied(false), 2000)
  }

  const handleDownload = () => {
    const blob = new Blob([answer], { type: 'text/markdown' })
    const url = URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    a.download = `edumate_${targetMarks ? `${targetMarks}m_` : ''}${Date.now()}.md`
    a.click()
    URL.revokeObjectURL(url)
  }

  const handleDocToggle = (docId) => {
    setSelectedDocIds(prev =>
      prev.includes(docId) ? prev.filter(id => id !== docId) : [...prev, docId]
    )
  }

  const selectedMarksObj = MARKS_OPTIONS.find(m => m.value === targetMarks)

  return (
    <div className="max-w-3xl mx-auto space-y-5">
      {/* Unified Input & Configuration Surface */}
      <div className="bg-dark-800 border border-white/[0.08] rounded-xl p-4 space-y-4">
        {/* Top Controls: Mode & Mark Selector */}
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 pb-3 border-b border-white/[0.06]">
          {/* Mode Switch */}
          <div className="flex items-center gap-2">
            <div className="flex bg-dark-900 p-0.5 rounded-lg border border-white/[0.06]">
              <button
                onClick={() => setDirectMode(true)}
                className={`flex items-center gap-1.5 px-3 py-1.5 rounded-md text-xs font-medium transition-colors ${
                  directMode
                    ? 'bg-dark-750 text-gray-100 border border-white/[0.08]'
                    : 'text-gray-400 hover:text-gray-200'
                }`}
              >
                <Zap size={13} className={directMode ? 'text-accent' : 'text-gray-400'} />
                <span>Fast Direct AI</span>
              </button>
              <button
                onClick={() => setDirectMode(false)}
                className={`flex items-center gap-1.5 px-3 py-1.5 rounded-md text-xs font-medium transition-colors ${
                  !directMode
                    ? 'bg-dark-750 text-gray-100 border border-white/[0.08]'
                    : 'text-gray-400 hover:text-gray-200'
                }`}
              >
                <BookOpen size={13} className={!directMode ? 'text-accent' : 'text-gray-400'} />
                <span>Grounded RAG</span>
              </button>
            </div>
            <span className="text-[12px] text-gray-400">
              {directMode ? 'General tutor' : 'Strictly from notes'}
            </span>
          </div>

          {/* Exam Mark Selector */}
          <div className="flex items-center gap-1 bg-dark-900 p-0.5 rounded-lg border border-white/[0.06] overflow-x-auto">
            {MARKS_OPTIONS.map(opt => (
              <button
                key={opt.label}
                onClick={() => setTargetMarks(opt.value)}
                title={opt.desc}
                className={`px-2.5 py-1 rounded text-xs font-medium transition-colors ${
                  targetMarks === opt.value
                    ? 'bg-dark-750 text-gray-100 border border-white/[0.08]'
                    : 'text-gray-400 hover:text-gray-200'
                }`}
              >
                {opt.label}
              </button>
            ))}
          </div>
        </div>

        {/* Document Selection (Visible only in Grounded RAG mode) */}
        {!directMode && (
          <div className="space-y-1.5 pt-1">
            <div className="flex items-center justify-between text-xs text-gray-400">
              <span>Filter study notes (leave empty to search all)</span>
              {selectedDocIds.length > 0 && (
                <button
                  onClick={() => setSelectedDocIds([])}
                  className="text-gray-400 hover:text-gray-200 text-[11px]"
                >
                  Clear selection
                </button>
              )}
            </div>
            <div className="flex flex-wrap gap-1.5 max-h-24 overflow-y-auto pt-1">
              {documents.length === 0 ? (
                <p className="text-xs text-gray-500 italic">No notes indexed yet. Upload a PDF first.</p>
              ) : (
                documents.map(doc => {
                  const isChecked = selectedDocIds.includes(doc.document_id)
                  return (
                    <button
                      key={doc.document_id}
                      onClick={() => handleDocToggle(doc.document_id)}
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
        )}

        {/* Question Textarea & Submit */}
        <div className="space-y-2">
          <textarea
            value={question}
            onChange={e => setQuestion(e.target.value)}
            onKeyDown={handleKeyDown}
            placeholder="Ask a question..."
            rows={3}
            className="w-full bg-dark-900 border border-white/[0.08] rounded-lg px-3.5 py-2.5 text-sm text-gray-100 placeholder-gray-500 focus:outline-none focus:border-white/20 transition-colors resize-none leading-relaxed"
          />

          <div className="flex items-center justify-between pt-1">
            <span className="text-[11px] text-gray-400 font-mono">
              Press <kbd className="px-1.5 py-0.5 bg-dark-750 border border-white/[0.08] rounded text-gray-300">Ctrl</kbd> + <kbd className="px-1.5 py-0.5 bg-dark-750 border border-white/[0.08] rounded text-gray-300">Enter</kbd> to ask
            </span>

            <div className="flex items-center gap-2">
              {streaming ? (
                <button
                  onClick={handleStop}
                  className="px-3.5 py-1.5 bg-dark-750 hover:bg-dark-700 text-negative border border-negative/30 text-xs font-medium rounded-md transition-colors"
                >
                  Stop
                </button>
              ) : (
                <button
                  onClick={handleAsk}
                  disabled={!question.trim()}
                  className="flex items-center gap-1.5 px-4 py-1.5 bg-gray-100 hover:bg-white text-dark-950 text-xs font-medium rounded-md transition-colors disabled:opacity-40 disabled:hover:bg-gray-100 cursor-pointer shadow-sm"
                >
                  <Send size={13} />
                  <span>Ask</span>
                </button>
              )}
            </div>
          </div>
        </div>
      </div>

      {/* Error alert */}
      {error && (
        <div className="flex items-center gap-2 bg-dark-800 border border-negative/30 text-negative text-xs p-3 rounded-lg">
          <AlertTriangle size={14} className="shrink-0" />
          <span>{error}</span>
        </div>
      )}

      {/* Response Display Area (The Moment) */}
      {(answer || streaming) && (
        <div className="bg-dark-800 border border-white/[0.08] rounded-xl overflow-hidden">
          {/* Response Meta Header */}
          <div className="flex items-center justify-between px-5 py-3 border-b border-white/[0.06] bg-dark-850">
            <div className="flex items-center gap-3">
              <span className="text-xs font-medium text-gray-200">
                Answer
              </span>
              {fallback && (
                <span className="text-[11px] text-accent bg-dark-750 px-2 py-0.5 rounded border border-white/[0.08]">
                  From AI knowledge (not in notes)
                </span>
              )}
            </div>

            <div className="flex items-center gap-3 text-xs text-gray-400 font-mono">
              <span className="flex items-center gap-1">
                <Clock size={12} /> {elapsed}s
              </span>
              <span>~{tokenCount} words</span>
              {elapsed > 0 && tokenCount > 0 && (
                <span>{(tokenCount / elapsed * 5).toFixed(1)} tok/s</span>
              )}
            </div>
          </div>

          {/* Answer Body */}
          <div ref={answerRef} className="p-6 max-h-[75vh] overflow-y-auto">
            {!answer && streaming && (
              <div className="flex items-center gap-2 text-xs text-gray-400 py-3">
                <Loader2 size={14} className="animate-spin text-accent" />
                <span>
                  {directMode
                    ? `Formulating ${targetMarks ? `${targetMarks}-mark ` : ''}answer...`
                    : `Searching notes and formulating ${targetMarks ? `${targetMarks}-mark ` : ''}grounded answer...`}
                </span>
              </div>
            )}

            <div className={`markdown-body ${streaming ? 'streaming-cursor' : ''}`}>
              <MarkdownErrorBoundary content={answer}>
                <ReactMarkdown
                  remarkPlugins={[remarkGfm, remarkMath]}
                  rehypePlugins={[[rehypeKatex, { throwOnError: false, strict: false }]]}
                >
                  {answer}
                </ReactMarkdown>
              </MarkdownErrorBoundary>
            </div>
          </div>

          {/* Action Row */}
          {!streaming && answer && (
            <div className="flex items-center justify-between px-5 py-2.5 border-t border-white/[0.06] bg-dark-850">
              <div className="flex items-center gap-2">
                <button
                  onClick={handleCopy}
                  className="flex items-center gap-1.5 text-xs text-gray-400 hover:text-gray-200 bg-dark-800 hover:bg-dark-750 px-3 py-1.5 rounded-md transition-colors border border-white/[0.06]"
                >
                  {copied ? <Check size={13} className="text-positive" /> : <Copy size={13} />}
                  <span>{copied ? 'Copied' : 'Copy'}</span>
                </button>
                <button
                  onClick={handleDownload}
                  className="flex items-center gap-1.5 text-xs text-gray-400 hover:text-gray-200 bg-dark-800 hover:bg-dark-750 px-3 py-1.5 rounded-md transition-colors border border-white/[0.06]"
                >
                  <Download size={13} />
                  <span>Download .md</span>
                </button>
              </div>

              <button
                onClick={handleAsk}
                className="flex items-center gap-1.5 text-xs text-gray-400 hover:text-gray-200 bg-dark-800 hover:bg-dark-750 px-3 py-1.5 rounded-md transition-colors border border-white/[0.06]"
              >
                <RotateCcw size={13} />
                <span>Regenerate</span>
              </button>
            </div>
          )}

          {/* Sources Section */}
          {!streaming && sources.length > 0 && (
            <div className="border-t border-white/[0.06]">
              <button
                onClick={() => setShowSources(!showSources)}
                className="w-full flex items-center justify-between px-5 py-2.5 text-xs text-gray-400 hover:text-gray-200 transition-colors"
              >
                <span className="flex items-center gap-2">
                  <BookOpen size={13} />
                  <span>Citations & Sources ({sources.length})</span>
                </span>
                <ChevronDown size={14} className={`transition-transform duration-150 ${showSources ? 'rotate-180' : ''}`} />
              </button>

              {showSources && (
                <div className="px-5 pb-4 space-y-2">
                  {sources.map((src, i) => (
                    <div
                      key={i}
                      className="bg-dark-900 border border-white/[0.06] rounded-md p-3 space-y-1.5"
                    >
                      <div className="flex items-center gap-2">
                        <span className="font-mono text-accent text-[11px] font-medium bg-dark-750 px-1.5 py-0.5 rounded border border-white/[0.08]">
                          [{src.source_number}]
                        </span>
                        <span className="text-xs font-medium text-gray-200">{src.document_name}</span>
                        <span className="text-[11px] text-gray-400 font-mono">Page {src.page_number}</span>
                      </div>
                      <p className="text-xs text-gray-400 leading-relaxed font-mono text-[12px] pl-2 border-l border-white/[0.08]">
                        {src.chunk_text}
                      </p>
                    </div>
                  ))}
                </div>
              )}
            </div>
          )}
        </div>
      )}
    </div>
  )
}
