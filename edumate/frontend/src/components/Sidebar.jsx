import { useState, useRef } from 'react'
import { uploadDocument } from '../utils/api'
import {
  User, Upload, FileText, ChevronLeft,
  BookOpen, Hash, Loader2, CheckCircle2, AlertCircle
} from 'lucide-react'

const LEVELS = [
  'Class 8', 'Class 9', 'Class 10', 'Class 11', 'Class 12',
  'Undergraduate', 'Postgraduate'
]

export default function Sidebar({
  open, onToggle, studentId, setStudentId,
  studentLevel, setStudentLevel, documents, onDocumentUploaded
}) {
  const [uploading, setUploading] = useState(false)
  const [uploadMsg, setUploadMsg] = useState(null)
  const [subject, setSubject] = useState('')
  const [chapter, setChapter] = useState('')
  const fileRef = useRef(null)

  const handleUpload = async () => {
    const file = fileRef.current?.files?.[0]
    if (!file) return

    setUploading(true)
    setUploadMsg(null)
    try {
      const result = await uploadDocument(file, studentId, subject || 'General', chapter || 'General')
      setUploadMsg({ type: 'success', text: `Indexed "${result.document_name}" (${result.number_of_chunks} chunks)` })
      fileRef.current.value = ''
      onDocumentUploaded()
    } catch (e) {
      setUploadMsg({ type: 'error', text: e.message })
    } finally {
      setUploading(false)
    }
  }

  if (!open) return null

  return (
    <aside className="w-[268px] bg-dark-900 border-r border-white/[0.08] flex flex-col shrink-0 h-full text-gray-200">
      {/* Header */}
      <div className="h-14 flex items-center justify-between px-4 border-b border-white/[0.08]">
        <span className="text-xs font-medium text-gray-300">Settings & Material</span>
        <button
          onClick={onToggle}
          title="Close sidebar"
          className="p-1 text-gray-400 hover:text-gray-200 hover:bg-dark-750 rounded transition-colors"
        >
          <ChevronLeft size={16} />
        </button>
      </div>

      <div className="flex-1 overflow-y-auto p-4 space-y-6">
        {/* Student Profile */}
        <section className="space-y-3">
          <div className="flex items-center gap-2 text-xs font-medium text-gray-300">
            <User size={14} className="text-gray-400" />
            <span>Student profile</span>
          </div>
          <div className="space-y-2">
            <div>
              <label className="text-[12px] text-gray-400 block mb-1">Student ID</label>
              <input
                value={studentId}
                onChange={e => setStudentId(e.target.value)}
                className="w-full bg-dark-800 border border-white/[0.08] rounded-md px-3 py-1.5 text-xs text-gray-100 focus:outline-none focus:border-white/20 transition-colors"
              />
            </div>
            <div>
              <label className="text-[12px] text-gray-400 block mb-1">Academic level</label>
              <select
                value={studentLevel}
                onChange={e => setStudentLevel(e.target.value)}
                className="w-full bg-dark-800 border border-white/[0.08] rounded-md px-2.5 py-1.5 text-xs text-gray-100 focus:outline-none focus:border-white/20 transition-colors"
              >
                {LEVELS.map(l => <option key={l} value={l}>{l}</option>)}
              </select>
            </div>
          </div>
        </section>

        {/* Upload Material */}
        <section className="space-y-3">
          <div className="flex items-center gap-2 text-xs font-medium text-gray-300">
            <Upload size={14} className="text-gray-400" />
            <span>Upload study material</span>
          </div>
          <div className="space-y-2">
            <input
              ref={fileRef}
              type="file"
              accept=".pdf"
              className="w-full text-xs text-gray-400 file:mr-2 file:py-1 file:px-2.5 file:rounded file:border-0 file:text-xs file:font-medium file:bg-dark-700 file:text-gray-200 hover:file:bg-dark-600 bg-dark-800 rounded-md border border-white/[0.08] p-1.5 cursor-pointer"
            />
            <div className="grid grid-cols-2 gap-2">
              <input
                value={subject}
                onChange={e => setSubject(e.target.value)}
                placeholder="Subject"
                className="bg-dark-800 border border-white/[0.08] rounded-md px-2.5 py-1.5 text-xs text-gray-100 placeholder-gray-500 focus:outline-none focus:border-white/20"
              />
              <input
                value={chapter}
                onChange={e => setChapter(e.target.value)}
                placeholder="Chapter"
                className="bg-dark-800 border border-white/[0.08] rounded-md px-2.5 py-1.5 text-xs text-gray-100 placeholder-gray-500 focus:outline-none focus:border-white/20"
              />
            </div>
            <button
              onClick={handleUpload}
              disabled={uploading}
              className="w-full flex items-center justify-center gap-2 bg-dark-750 hover:bg-dark-700 text-gray-100 text-xs font-medium py-2 rounded-md border border-white/[0.08] transition-colors disabled:opacity-50"
            >
              {uploading ? <Loader2 size={14} className="animate-spin text-accent" /> : <Upload size={14} className="text-gray-300" />}
              <span>{uploading ? 'Indexing PDF...' : 'Index PDF notes'}</span>
            </button>
            {uploadMsg && (
              <div className={`flex items-start gap-1.5 text-xs p-2 rounded-md border ${
                uploadMsg.type === 'success'
                  ? 'bg-dark-800 border-positive/30 text-positive'
                  : 'bg-dark-800 border-negative/30 text-negative'
              }`}>
                {uploadMsg.type === 'success'
                  ? <CheckCircle2 size={14} className="mt-0.5 shrink-0" />
                  : <AlertCircle size={14} className="mt-0.5 shrink-0" />}
                <span className="leading-snug">{uploadMsg.text}</span>
              </div>
            )}
          </div>
        </section>

        {/* Indexed Documents */}
        <section className="space-y-3">
          <div className="flex items-center justify-between text-xs font-medium text-gray-300">
            <span className="flex items-center gap-2">
              <BookOpen size={14} className="text-gray-400" />
              <span>Indexed notes</span>
            </span>
            <span className="text-[12px] text-gray-500 font-mono">{documents.length}</span>
          </div>

          <div className="space-y-1.5 max-h-72 overflow-y-auto">
            {documents.length === 0 ? (
              <p className="text-xs text-gray-500 italic py-2">No documents indexed yet.</p>
            ) : (
              documents.map(doc => (
                <div
                  key={doc.document_id}
                  className="bg-dark-800 border border-white/[0.06] rounded-md p-2.5 hover:border-white/[0.12] transition-colors"
                >
                  <div className="flex items-start gap-2">
                    <FileText size={14} className="text-gray-400 mt-0.5 shrink-0" />
                    <div className="min-w-0 flex-1">
                      <p className="text-xs font-medium text-gray-200 truncate" title={doc.document_name}>
                        {doc.document_name}
                      </p>
                      <div className="flex items-center gap-2 mt-1 text-[11px] text-gray-400 font-mono">
                        <span>ID:{doc.document_id}</span>
                        <span>•</span>
                        <span>{doc.number_of_pages}p</span>
                        <span>•</span>
                        <span>{doc.number_of_chunks} chunks</span>
                      </div>
                      {(doc.subject || doc.chapter) && (
                        <p className="text-[11px] text-gray-400 mt-0.5 truncate">
                          {doc.subject} · {doc.chapter}
                        </p>
                      )}
                    </div>
                  </div>
                </div>
              ))
            )}
          </div>
        </section>
      </div>

      {/* Footer */}
      <div className="px-4 py-3 border-t border-white/[0.08] text-center">
        <p className="text-[11px] text-gray-500 font-mono">
          EduMate • Local Gemma • Offline
        </p>
      </div>
    </aside>
  )
}
