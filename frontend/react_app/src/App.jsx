import { useEffect, useRef, useState } from 'react'
import './App.css'
import { Icon } from './components/ApplicationShell.jsx'
import ApplicationShell from './components/ApplicationShell.jsx'
import { useAuth } from './auth/useAuth.js'
import DashboardPage from './components/DashboardPage.jsx'
import EvidenceInspector from './components/EvidenceInspector.jsx'
import DatasetCharts from './components/DatasetCharts.jsx'
import MarkdownAnswer from './components/MarkdownAnswer.jsx'
import PlaceholderPage from './components/PlaceholderPage.jsx'
import AboutDeveloper from './components/AboutDeveloper.jsx'
import AuthScreen from './components/AuthScreen.jsx'

const starterQuestions = [
  'Plot a chart of monthly mean sea surface temperature from January through March 2020.',
  'What do the papers say about ocean temperature profiles?',
  'How does the dataset compare with published findings?',
]

const routeLabels = {
  data: 'Ocean data',
  paper: 'Research papers',
  both: 'Data + papers',
  none: 'General answer',
}

function normalizePath(path) {
  return path === '/' || path === '/login' ? '/dashboard' : path
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

function WorkspaceApp() {
  const { session, appRole, signOut } = useAuth()
  const [messages, setMessages] = useState([])
  const [query, setQuery] = useState('')
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')
  const [yearFrom, setYearFrom] = useState('')
  const [yearTo, setYearTo] = useState('')
  const [verifyCitations, setVerifyCitations] = useState(false)
  const [copiedMessage, setCopiedMessage] = useState(null)
  const [initialPath] = useState(() => normalizePath(window.location.pathname || '/'))
  const [currentPath, setCurrentPath] = useState(initialPath)
  const [theme, setTheme] = useState(() => window.localStorage.getItem('nerivane-theme') === 'dark' ? 'dark' : 'light')
  const [loginOpen, setLoginOpen] = useState(() => window.location.pathname === '/login')
  const visiblePath = currentPath
  const [sidebarCollapsed, setSidebarCollapsed] = useState(false)
  const [mobileSidebarOpen, setMobileSidebarOpen] = useState(false)
  const [activeConversationId, setActiveConversationId] = useState(() => Date.now())
  const [conversations, setConversations] = useState([])
  const [shareStatus, setShareStatus] = useState('')
  const [inspectorOpen, setInspectorOpen] = useState(() => window.matchMedia('(min-width: 1181px)').matches)
  const [inspectorTab, setInspectorTab] = useState('sources')
  const [evidenceMessageId, setEvidenceMessageId] = useState(null)
  const [selectedSourceId, setSelectedSourceId] = useState(null)
  const [selectedChunkIndex, setSelectedChunkIndex] = useState(null)
  const [citationRequestId, setCitationRequestId] = useState(0)
  const bottomRef = useRef(null)
  const queryInputRef = useRef(null)
  const messageIdRef = useRef(0)

  useEffect(() => {
    document.documentElement.dataset.theme = theme
    document.body.classList.toggle('dark', theme === 'dark')
    window.localStorage.setItem('nerivane-theme', theme)
  }, [theme])

  useEffect(() => {
    const updatePath = () => {
      const requestedPath = normalizePath(window.location.pathname || '/')
      setCurrentPath(requestedPath)
    }
    window.addEventListener('popstate', updatePath)
    return () => window.removeEventListener('popstate', updatePath)
  }, [session])

  useEffect(() => {
    if (window.location.pathname !== visiblePath) {
      window.history.replaceState({}, '', visiblePath)
    }
  }, [visiblePath])

  function navigate(path) {
    const nextPath = normalizePath(path)
    if (window.location.pathname !== nextPath) window.history.pushState({}, '', nextPath)
    setCurrentPath(nextPath)
  }

  function requestLogin() {
    setLoginOpen(true)
  }

  function startNewChat() {
    if (messages.length) {
      const current = {
        id: activeConversationId,
        title: messages.find((message) => message.role === 'user')?.text.slice(0, 56) || 'Research conversation',
        messages,
        updatedAt: messages.at(-1)?.createdAt || null,
      }
      setConversations((existing) => [current, ...existing.filter((conversation) => conversation.id !== current.id)])
    }
    setMessages([])
    setQuery('')
    setError('')
    setActiveConversationId(Date.now())
    setEvidenceMessageId(null)
    setSelectedSourceId(null)
    setSelectedChunkIndex(null)
    setInspectorTab('sources')
    navigate('/research-assistant')
    setMobileSidebarOpen(false)
  }

  function selectConversation(conversationId) {
    if (!session) {
      requestLogin()
      return
    }
    const current = messages.length ? {
      id: activeConversationId,
      title: messages.find((message) => message.role === 'user')?.text.slice(0, 56) || 'Research conversation',
      messages,
      updatedAt: messages.at(-1)?.createdAt || null,
    } : null
    const candidates = current ? [current, ...conversations] : conversations
    const selected = candidates.find((conversation) => conversation.id === conversationId)
    if (!selected) return
    if (current) setConversations((existing) => [current, ...existing.filter((conversation) => conversation.id !== current.id)])
    setMessages(selected.messages)
    setActiveConversationId(selected.id)
    const latestAssistant = [...selected.messages].reverse().find((message) => message.role === 'assistant')
    setEvidenceMessageId(latestAssistant?.messageId ?? null)
    setSelectedSourceId(latestAssistant?.paperSources?.[0]?.source_id ?? null)
    setSelectedChunkIndex(null)
    setQuery('')
    setError('')
    navigate('/research-assistant')
  }

  const latestAssistantPreview = [...messages].reverse().find((message) => message.role === 'assistant')?.text
  const currentConversation = messages.length ? {
    id: activeConversationId,
    title: messages.find((message) => message.role === 'user')?.text.slice(0, 56) || 'Research conversation',
    preview: (latestAssistantPreview || messages.at(-1)?.text || '').replace(/\s+/g, ' ').trim(),
    messages,
    updatedAt: messages.at(-1)?.createdAt || null,
  } : null
  const recentConversations = currentConversation
    ? [currentConversation, ...conversations.filter((conversation) => conversation.id !== currentConversation.id)]
    : conversations

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth', block: 'end' })
  }, [messages, loading])

  useEffect(() => {
    const input = queryInputRef.current
    if (!input) return
    input.style.height = 'auto'
    input.style.height = `${Math.min(input.scrollHeight, 180)}px`
    input.style.overflowY = input.scrollHeight > 180 ? 'auto' : 'hidden'
  }, [query])

  async function sendMessage(value = query, sourceMode = null) {
    if (!session) {
      requestLogin()
      return
    }
    const text = value.trim()
    if (!text || loading) return
    if (yearFrom && yearTo && Number(yearFrom) > Number(yearTo)) {
      setError('The starting publication year must be earlier than the ending year.')
      return
    }

    setMessages((current) => [...current, { role: 'user', text, createdAt: new Date().toISOString() }])
    setQuery('')
    setError('')
    setLoading(true)

    try {
      const sourceDirective = {
        papers: '[[NERIVANE_SOURCE_MODE:PAPERS]]',
        dataset: '[[NERIVANE_SOURCE_MODE:DATASET]]',
        both: '[[NERIVANE_SOURCE_MODE:BOTH]]',
      }[sourceMode]
      const requestQuery = sourceDirective ? `${sourceDirective}\n${text}` : text
      const response = await fetch('/api/chat', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          Authorization: 'Bearer ' + session.access_token,
        },
        body: JSON.stringify({
          query: requestQuery,
          ...(yearFrom ? { publication_year_from: Number(yearFrom) } : {}),
          ...(yearTo ? { publication_year_to: Number(yearTo) } : {}),
          verify_citations: verifyCitations,
        }),
      })
      const result = await response.json()

      if (!response.ok) {
        throw new Error(result.detail || `Request failed (${response.status})`)
      }

      const assistantMessage = {
          role: 'assistant',
          text: result.answer,
          createdAt: new Date().toISOString(),
          route: result.route,
          sourceErrors: result.source_errors,
          paperSources: result.paper_sources || [],
          paperChunks: result.paper_chunks || [],
          rawDataOutput: result.raw_data_output ?? null,
          citationWarnings: result.citation_warnings || [],
          claimChecks: result.claim_checks || [],
          claimCheckStatus: result.claim_check_status || 'not_requested',
          messageId: ++messageIdRef.current,
        }
      setMessages((current) => [...current, assistantMessage])
      setEvidenceMessageId(assistantMessage.messageId)
      setSelectedSourceId(assistantMessage.paperSources[0]?.source_id ?? null)
      setSelectedChunkIndex(null)
      setInspectorTab(assistantMessage.paperSources.length ? 'sources' : assistantMessage.rawDataOutput ? 'dataset' : 'details')
    } catch (requestError) {
      const message = requestError instanceof TypeError
        ? 'Could not reach the backend. Make sure FastAPI is running on port 8000.'
        : requestError.message
      setError(message)
      setMessages((current) => [
        ...current,
        { role: 'assistant', text: `I couldn’t complete that request. ${message}`, failed: true, createdAt: new Date().toISOString() },
      ])
    } finally {
      setLoading(false)
    }
  }

  function handleSubmit(event) {
    event.preventDefault()
    sendMessage()
  }

  function startResearchFromDashboard(text, sourceMode) {
    if (loading) return
    if (!session) {
      requestLogin()
      return
    }
    startNewChat()
    sendMessage(text, sourceMode)
  }

  function handleCitationClick(source, page, messageId) {
    const message = messages.find((item) => item.messageId === messageId)
    const excerpts = source.excerpts || []
    const chunkIndex = page == null ? 0 : excerpts.findIndex((excerpt) => Number(excerpt.page_number) === page)
    setEvidenceMessageId(message?.messageId ?? messageId)
    setSelectedSourceId(source.source_id)
    setSelectedChunkIndex(chunkIndex >= 0 && excerpts.length ? chunkIndex : excerpts.length ? 0 : null)
    setCitationRequestId((current) => current + 1)
    setInspectorTab('sources')
    setInspectorOpen(true)
  }

  function selectEvidenceSource(source) {
    setSelectedSourceId((current) => current === source.source_id ? null : source.source_id)
    setSelectedChunkIndex(null)
  }

  async function copyReferences(message) {
    const sources = message?.paperSources || []
    if (!sources.length) return
    const citedReferences = sources.filter((source) => source.cited).map((source) => source.reference)
    const references = (citedReferences.length ? citedReferences : sources.map((source) => source.reference)).join('\n')
    try {
      await navigator.clipboard.writeText(references)
      setCopiedMessage(message.messageId)
    } catch {
      setError('Clipboard access is unavailable in this browser.')
    }
  }

  function conversationText() {
    return messages.map((message) => `${message.role === 'user' ? 'You' : 'Nerivane'}:\n${message.text}`).join('\n\n')
  }

  async function shareConversation() {
    if (!messages.length) return
    const text = conversationText()
    try {
      if (navigator.share) {
        await navigator.share({ title: conversationTitle, text })
        setShareStatus('Shared')
      } else {
        await navigator.clipboard.writeText(text)
        setShareStatus('Copied')
      }
    } catch (shareError) {
      if (shareError.name !== 'AbortError') setError('Sharing is unavailable in this browser.')
    }
    window.setTimeout(() => setShareStatus(''), 1800)
  }

  async function copyConversation() {
    if (!messages.length) return
    try {
      await navigator.clipboard.writeText(conversationText())
      setShareStatus('Copied')
      window.setTimeout(() => setShareStatus(''), 1800)
    } catch {
      setError('Clipboard access is unavailable in this browser.')
    }
  }

  const firstQuestion = messages.find((message) => message.role === 'user')?.text
  const conversationTitle = firstQuestion
    ? `${firstQuestion.slice(0, 66)}${firstQuestion.length > 66 ? '…' : ''}`
    : 'New research conversation'
  const latestRoute = [...messages].reverse().find((message) => message.role === 'assistant' && message.route)?.route
  const latestAssistantMessage = [...messages].reverse().find((message) => message.role === 'assistant')
  const evidenceMessage = messages.find((message) => message.messageId === evidenceMessageId) || latestAssistantMessage

  return (
    <>
    <ApplicationShell
      currentPath={visiblePath}
      navigate={navigate}
      collapsed={sidebarCollapsed}
      onToggleCollapsed={() => setSidebarCollapsed((collapsed) => !collapsed)}
      mobileOpen={mobileSidebarOpen}
      onToggleMobile={() => setMobileSidebarOpen((open) => !open)}
      onCloseMobile={() => setMobileSidebarOpen(false)}
      conversations={recentConversations}
      activeConversationId={activeConversationId}
      onNewChat={startNewChat}
      onSelectConversation={selectConversation}
      busy={loading}
      user={session?.user}
      appRole={appRole}
      onSignOut={signOut}
      onSignIn={requestLogin}
    >
      {visiblePath === '/dashboard' ? <DashboardPage conversations={recentConversations} onStartResearch={startResearchFromDashboard} onOpenConversation={selectConversation} loading={loading} isAuthenticated={Boolean(session)} onRequestLogin={requestLogin} />
        : visiblePath === '/about' ? <AboutDeveloper />
        : visiblePath === '/research-assistant' ? <div className="research-assistant-page">
      <header className="conversation-header">
        <div className="assistant-header-left">
          <button className="icon-button mobile-menu-button" type="button" aria-label="Open navigation" onClick={() => setMobileSidebarOpen((open) => !open)}><Icon name="menu" /></button>
          <div className="conversation-title-block">
            <span className="conversation-eyebrow">NERIVANE WORKSPACE / RESEARCH ASSISTANT</span>
            <h2 title={conversationTitle}>{conversationTitle}</h2>
          </div>
        </div>
        <div className="conversation-tools">
          <div className="topbar-status"><span className="status-dot" /><span>Research assistant</span></div>
          <div className="source-routing-indicator" title="The router chooses data, papers, both, or a general response for each question.">
            <span className="routing-dot" />
            <span>Auto routing</span>
            {latestRoute && <span className="routing-divider">·</span>}
            {latestRoute && <strong>{routeLabels[latestRoute] || latestRoute}</strong>}
          </div>
          <button className={`conversation-action evidence-toggle${inspectorOpen ? ' is-active' : ''}`} type="button" aria-expanded={inspectorOpen} aria-controls="evidence-inspector" onClick={() => setInspectorOpen((open) => !open)}><Icon name="papers" /><span>Evidence</span></button>
          <button className="conversation-action" type="button" onClick={shareConversation} disabled={!messages.length} title="Share conversation">{shareStatus === 'Shared' ? 'Shared' : <><Icon name="shared" /><span>Share</span></>}</button>
          <button className="conversation-action conversation-copy-action" type="button" onClick={copyConversation} disabled={!messages.length} title="Copy conversation transcript">{shareStatus === 'Copied' ? 'Copied' : 'Copy transcript'}</button>
        </div>
      </header>
      <div className="research-workspace">
      <div className="conversation-column">
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
                      ? <MarkdownAnswer text={message.text} sources={message.paperSources || []} messageId={message.messageId} onCitationClick={handleCitationClick} />
                      : message.text}
                  </div>
                  {message.role === 'assistant' && message.rawDataOutput && <DatasetCharts rawDataOutput={message.rawDataOutput} />}
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
        <div className="composer-context-row">
          <span className="composer-routing-label"><span className="routing-dot" /> Sources selected automatically per question</span>
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
        </div>
        <form className="composer" onSubmit={handleSubmit}>
          <label className="sr-only" htmlFor="chat-input">Your question</label>
            <textarea
            ref={queryInputRef}
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
            placeholder="Ask a research question…"
            onFocus={() => { if (!session) { requestLogin(); queryInputRef.current?.blur() } }}
            onClick={() => { if (!session) requestLogin() }}
            disabled={loading}
          />
          <button className="send-button" type="submit" disabled={loading || !query.trim()} aria-label="Send message">
            {loading ? <span className="send-loading" aria-hidden="true" /> : <Icon name="send" className="send-icon" />}
          </button>
        </form>
        <p className="composer-hint">Enter to send · Shift + Enter for a new line</p>
      </footer>
      </div>
      <EvidenceInspector
        open={inspectorOpen}
        activeTab={inspectorTab}
        onSelectTab={setInspectorTab}
        onClose={() => setInspectorOpen(false)}
        message={evidenceMessage}
        selectedSourceId={selectedSourceId}
        selectedChunkIndex={selectedChunkIndex}
        citationRequestId={citationRequestId}
        onSelectSource={selectEvidenceSource}
        onCopyReferences={copyReferences.bind(null, evidenceMessage)}
        onDownloadBibtex={downloadBibtex}
        copiedMessage={copiedMessage}
      />
      </div>
      </div> : <PlaceholderPage path={visiblePath} theme={theme} onThemeChange={setTheme} />}
    </ApplicationShell>
    {!session && loginOpen && <AuthScreen onCancel={() => setLoginOpen(false)} onAuthenticated={() => setLoginOpen(false)} />}
    </>
  )
}

function App() {
  const { loading } = useAuth()
  if (loading) return <main className="auth-loading">Restoring your session…</main>
  return <WorkspaceApp />
}

export default App
