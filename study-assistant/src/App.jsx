// App.jsx – Component gốc mỏng (thin root)


import React from 'react'
import StudyAssistantApp from './StudyAssistantApp.jsx'

export default function App() {
  return (
    <div className="min-h-screen bg-gray-50">
      {/* Header rất nhẹ (tuỳ ý), bạn có thể dời nó vào StudyAssistantApp nếu thích) */}
      <header className="border-b bg-white">
        <div className="mx-auto max-w-7xl px-4 py-4 flex items-center justify-between">
          <div className="flex items-center gap-2">
            <div className="h-9 w-9 rounded-xl bg-black text-white flex items-center justify-center font-bold">AI</div>
            <h1 className="text-xl font-semibold">Study Assistant</h1>
            <span className="ml-2 rounded-full border px-2 py-0.5 text-xs text-gray-600">Frontend</span>
          </div>
          <div className="text-sm text-gray-600">Login</div>
        </div>
      </header>

      {/* Component chính chứa toàn bộ UX: Upload → Summary/Flashcards/Quiz/Chat */}
      <main className="mx-auto max-w-7xl px-4 py-6">
        <StudyAssistantApp />
      </main>

      <footer className="border-t bg-white">
        <div className="mx-auto max-w-7xl px-4 py-4 text-xs text-gray-500 flex items-center justify-between">
          <div>© {new Date().getFullYear()} Study Assistant – Demo UI</div>
          <div className="flex gap-3">
            <a className="hover:underline" href="#">Privacy</a>
            <a className="hover:underline" href="#">Terms</a>
          </div>
        </div>
      </footer>
    </div>
  )
}