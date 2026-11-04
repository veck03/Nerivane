import { useEffect, useRef, useState } from 'react'
import './App.css'

const starterQuestions = [
  'What is the average sea surface temperature in January?',
  'What do the papers say about ocean temperature profiles?',
  'How does the dataset compare with published findings?',
]

const routeLabels = {
  data: 'Ocean data',
  paper: 'Research papers',
  both: 'Data + papers',
  none: 'General answer',
}

function App() {
  const [messages, setMessages] = useState([])
  const [query, setQuery] = useState('')
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')
  const bottomRef = useRef(null)

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth', block: 'end' })
  }, [messages, loading])

  async function sendMessage(value = query) {
    const text = value.trim()
    if (!text || loading) return

    setMessages((current) => [...current, { role: 'user', text }])
    setQuery('')
    setError('')
    setLoading(true)

    try {
      const response = await fetch('/api/chat', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ query: text }),
      })
      const result = await response.json()

      if (!response.ok) {
        throw new Error(result.detail || `Request failed (${response.status})`)
      }

      setMessages((current) => [
        ...current,
        {
          role: 'assistant',
          text: result.answer,
          route: result.route,
          sourceErrors: result.source_errors,
        },
      ])
    } catch (requestError) {
      const message = requestError instanceof TypeError
        ? 'Could not reach the backend. Make sure FastAPI is running on port 8000.'
        : requestError.message
      setError(message)
      setMessages((current) => [
        ...current,
        { role: 'assistant', text: `I couldn’t complete that request. ${message}`, failed: true },
      ])
    } finally {
      setLoading(false)
    }
  }

  function handleSubmit(event) {
    event.preventDefault()
    sendMessage()
  }

  return (
    <main className="app-shell">
      <header className="topbar">
        <a className="brand" href="/" aria-label="Ocean Research home">
          <span className="brand-mark" aria-hidden="true">≈</span>
          <span>Ocean Research</span>
        </a>
        <span className="connection-label"><span className="status-dot" /> Research assistant</span>
      </header>

      <section className={`chat ${messages.length ? 'chat-active' : ''}`} aria-label="Chat">
        {messages.length === 0 ? (
          <div className="welcome">
            <div className="eyebrow">Ocean data · Research papers</div>
            <h1>What would you like<br />to explore?</h1>
            <p>Ask about the ocean dataset, indexed papers, or a question that needs both.</p>
            <div className="suggestions" aria-label="Suggested questions">
              {starterQuestions.map((question) => (
                <button key={question} type="button" onClick={() => sendMessage(question)}>
                  <span>{question}</span><span className="suggestion-arrow" aria-hidden="true">↗</span>
                </button>
              ))}
            </div>
          </div>
        ) : (
          <div className="message-list" aria-live="polite">
            {messages.map((message, index) => (
              <article className={`message-row ${message.role}`} key={`${index}-${message.role}`}>
                {message.role === 'assistant' && <div className="assistant-avatar" aria-hidden="true">≈</div>}
                <div className="message-content">
                  {message.role === 'assistant' && message.route && (
                    <div className="route-label">{routeLabels[message.route] || message.route}</div>
                  )}
                  <div className={`message-bubble ${message.failed ? 'message-failed' : ''}`}>
                    {message.text}
                  </div>
                  {message.sourceErrors && Object.keys(message.sourceErrors).length > 0 && (
                    <p className="source-note">A source could not be retrieved. The answer may be incomplete.</p>
                  )}
                </div>
              </article>
            ))}
            {loading && (
              <div className="message-row assistant" role="status" aria-label="Assistant is thinking">
                <div className="assistant-avatar" aria-hidden="true">≈</div>
                <div className="typing-indicator"><span /><span /><span /></div>
              </div>
            )}
            <div ref={bottomRef} />
          </div>
        )}
      </section>

      <footer className="composer-area">
        {error && <p className="connection-error" role="status">{error}</p>}
        <form className="composer" onSubmit={handleSubmit}>
          <label className="sr-only" htmlFor="chat-input">Your question</label>
          <textarea
            id="chat-input"
            rows="1"
            value={query}
            onChange={(event) => setQuery(event.target.value)}
            onKeyDown={(event) => {
              if (event.key === 'Enter' && !event.shiftKey) {
                event.preventDefault()
                handleSubmit(event)
              }
            }}
            placeholder="Ask a question..."
            disabled={loading}
          />
          <button className="send-button" type="submit" disabled={loading || !query.trim()} aria-label="Send message">
            {loading ? '…' : '↑'}
          </button>
        </form>
        <p className="composer-hint">Enter to send · Shift + Enter for a new line</p>
      </footer>
    </main>
  )
}

export default App
