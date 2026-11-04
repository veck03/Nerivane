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

function renderAnswerWithCitations(text, sources, messageId) {
  const sourceById = new Map(sources.map((source) => [source.source_id, source]))
  return text.split(/(\[S\d+(?:,\s*p\.?\s*\d+)?\])/gi).map((part, index) => {
    const match = part.match(/^\[(S\d+)(?:,\s*p\.?\s*(\d+))?\]$/i)
    const source = match ? sourceById.get(match[1].toUpperCase()) : null
    if (!source) return part
    return (
      <a
        className="inline-citation"
        href={`#source-${messageId}-${source.source_id}`}
        key={`${part}-${index}`}
        title={`Open ${source.title}${match[2] ? `, page ${match[2]}` : ''}`}
      >
        {part}
      </a>
    )
  })
}

function downloadBibtex(sources) {
  const selected = sources.filter((source) => source.cited)
  const entries = selected.length ? selected : sources
  const blob = new Blob([entries.map((source) => source.bibtex).join('\n\n')], {
    type: 'application/x-bibtex;charset=utf-8',
  })
  const url = URL.createObjectURL(blob)
  const anchor = document.createElement('a')
  anchor.href = url
  anchor.download = 'ocean-research-references.bib'
  anchor.click()
  URL.revokeObjectURL(url)
}

function App() {
  const [messages, setMessages] = useState([])
  const [query, setQuery] = useState('')
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')
  const [yearFrom, setYearFrom] = useState('')
  const [yearTo, setYearTo] = useState('')
  const [verifyCitations, setVerifyCitations] = useState(false)
  const [copiedMessage, setCopiedMessage] = useState(null)
  const bottomRef = useRef(null)

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth', block: 'end' })
  }, [messages, loading])

  async function sendMessage(value = query) {
    const text = value.trim()
    if (!text || loading) return
    if (yearFrom && yearTo && Number(yearFrom) > Number(yearTo)) {
      setError('The starting publication year must be earlier than the ending year.')
      return
    }

    setMessages((current) => [...current, { role: 'user', text }])
    setQuery('')
    setError('')
    setLoading(true)

    try {
      const response = await fetch('/api/chat', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          query: text,
          ...(yearFrom ? { publication_year_from: Number(yearFrom) } : {}),
          ...(yearTo ? { publication_year_to: Number(yearTo) } : {}),
          verify_citations: verifyCitations,
        }),
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
          paperSources: result.paper_sources || [],
          citationWarnings: result.citation_warnings || [],
          claimChecks: result.claim_checks || [],
          claimCheckStatus: result.claim_check_status || 'not_requested',
          messageId: Date.now(),
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
                    {message.role === 'assistant'
                      ? renderAnswerWithCitations(message.text, message.paperSources || [], message.messageId)
                      : message.text}
                  </div>
                  {message.role === 'assistant' && message.citationWarnings?.length > 0 && (
                    <p className="citation-warning" role="status">
                      Citation check: {message.citationWarnings.join(' ')}
                    </p>
                  )}
                  {message.role === 'assistant' && message.claimChecks?.length > 0 && (
                    <div className="claim-check-panel">
                      <p>AI support check · Review aid, not proof</p>
                      <ul className="claim-checks" aria-label="Optional claim support results">
                        {message.claimChecks.map((finding, findingIndex) => (
                          <li key={`${finding.status}-${findingIndex}`}>
                            <span className={`claim-status ${finding.status}`}>{finding.status}</span>
                            <span>{finding.claim}</span>
                            {finding.source_ids?.length > 0 && <small>Sources: {finding.source_ids.join(', ')}</small>}
                          </li>
                        ))}
                      </ul>
                    </div>
                  )}
                  {message.role === 'assistant' && message.claimCheckStatus === 'skipped' && (
                    <p className="claim-check-note">The optional support check was skipped because no source evidence was retrieved.</p>
                  )}
                  {message.role === 'assistant' && message.claimCheckStatus === 'not_applicable' && (
                    <p className="claim-check-note">Claim support checks run only when the query uses papers.</p>
                  )}
                  {message.role === 'assistant' && message.claimCheckStatus === 'completed' && message.claimChecks?.length === 0 && (
                    <p className="claim-check-note">The optional support check completed; it returned no claim findings.</p>
                  )}
                  {message.role === 'assistant' && message.paperSources?.length > 0 && (
                    <section className="source-panel" aria-label="Paper sources">
                      <div className="source-panel-header">
                        <strong>Paper sources</strong>
                        <div className="source-actions">
                          <button
                            type="button"
                            onClick={async () => {
                              const refs = message.paperSources
                                .filter((source) => source.cited)
                                .map((source) => source.reference)
                              const text = (refs.length ? refs : message.paperSources.map((source) => source.reference)).join('\n')
                              try {
                                await navigator.clipboard.writeText(text)
                                setCopiedMessage(message.messageId)
                              } catch {
                                setError('Clipboard access is unavailable in this browser.')
                              }
                            }}
                          >
                            {copiedMessage === message.messageId ? 'Copied' : 'Copy references'}
                          </button>
                          <button type="button" onClick={() => downloadBibtex(message.paperSources)}>
                            Download BibTeX
                          </button>
                        </div>
                      </div>
                      <ul className="source-list">
                        {message.paperSources.map((source) => (
                          <li id={`source-${message.messageId}-${source.source_id}`} key={source.source_id} className="source-card">
                            <div className="source-title-row">
                              <span className="source-id">[{source.source_id}]</span>
                              {source.paper_url ? (
                                <a href={source.paper_url} target="_blank" rel="noreferrer">{source.title}</a>
                              ) : <strong>{source.title}</strong>}
                              {source.cited && <span className="cited-tag">Cited</span>}
                            </div>
                            <p className="source-meta">
                              {source.authors || 'Unknown author'}
                              {source.publication_year ? ` · ${source.publication_year}` : ''}
                              {source.venue ? ` · ${source.venue}` : ''}
                              {source.pages?.length ? ` · Pages ${source.pages.join(', ')}` : ''}
                            </p>
                            {source.excerpts?.[0]?.text && (
                              <details className="source-excerpt">
                                <summary>View retrieved excerpt</summary>
                                <p>{source.excerpts[0].text}</p>
                              </details>
                            )}
                          </li>
                        ))}
                      </ul>
                    </section>
                  )}
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
        <div className="paper-filters" aria-label="Paper publication year filter">
          <span>Paper years</span>
          <label>
            <span className="sr-only">From publication year</span>
            <input type="number" min="1800" max="2100" placeholder="From" value={yearFrom} onChange={(event) => setYearFrom(event.target.value)} disabled={loading} />
          </label>
          <span className="filter-separator">to</span>
          <label>
            <span className="sr-only">To publication year</span>
            <input type="number" min="1800" max="2100" placeholder="To" value={yearTo} onChange={(event) => setYearTo(event.target.value)} disabled={loading} />
          </label>
          <span className="filter-hint">Applies to paper searches</span>
          <label className="verify-option">
            <input type="checkbox" checked={verifyCitations} onChange={(event) => setVerifyCitations(event.target.checked)} disabled={loading} />
            <span>Check claim support (extra model call)</span>
          </label>
        </div>
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
