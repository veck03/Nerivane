import { useState } from 'react'
import { Icon } from './ApplicationShell.jsx'
import './dashboard-page.css'

const sourceModes = [
  { id: 'papers', label: 'Papers', icon: 'papers' },
  { id: 'dataset', label: 'Dataset', icon: 'datasets' },
  { id: 'both', label: 'Both', icon: 'shared' },
]

const suggestions = [
  {
    title: 'Explore Scientific Literature',
    description: 'Find evidence and methods discussed across indexed research papers.',
    query: 'What do research papers report about ocean temperature profiles?',
    mode: 'papers',
    icon: 'papers',
    tone: 'indigo',
  },
  {
    title: 'Analyze Research Datasets',
    description: 'Ask for measurements and statistics from the master ocean dataset.',
    query: 'What is the average sea surface temperature in January 2020?',
    mode: 'dataset',
    icon: 'datasets',
    tone: 'teal',
  },
  {
    title: 'Compare Research Findings',
    description: 'Bring dataset measurements together with published evidence.',
    query: 'Compare January 2020 sea surface temperature with findings in research papers.',
    mode: 'both',
    icon: 'visualizations',
    tone: 'violet',
  },
]

function relativeTime(timestamp) {
  if (!timestamp) return 'Time not available'
  const time = new Date(timestamp).getTime()
  if (!Number.isFinite(time)) return 'Time not available'
  const elapsed = Math.max(0, Date.now() - time)
  const minutes = Math.floor(elapsed / 60000)
  if (minutes < 1) return 'Just now'
  if (minutes < 60) return `${minutes}m ago`
  const hours = Math.floor(minutes / 60)
  if (hours < 24) return `${hours}h ago`
  const days = Math.floor(hours / 24)
  if (days === 1) return 'Yesterday'
  if (days < 7) return `${days}d ago`
  return new Date(time).toLocaleDateString()
}

function conversationPreview(conversation) {
  const lastAssistant = [...(conversation.messages || [])].reverse().find((message) => message.role === 'assistant')
  const lastUser = [...(conversation.messages || [])].reverse().find((message) => message.role === 'user')
  return (lastAssistant?.text || lastUser?.text || '').replace(/\s+/g, ' ').trim()
}

export default function DashboardPage({ conversations, onStartResearch, onOpenConversation, loading }) {
  const [query, setQuery] = useState('')
  const [sourceMode, setSourceMode] = useState('both')

  function submitQuery(event) {
    event.preventDefault()
    const trimmedQuery = query.trim()
    if (!trimmedQuery || loading) return
    onStartResearch(trimmedQuery, sourceMode)
    setQuery('')
  }

  const stats = [
    { label: 'Indexed papers', value: '—', note: 'Corpus total is not exposed by the API', icon: 'papers', tone: 'indigo' },
    { label: 'Available datasets', value: '1', note: 'ocean_q1_2020.zarr · configured master', icon: 'datasets', tone: 'teal' },
    { label: 'Research conversations', value: String(conversations.length), note: 'In this browser session', icon: 'shared', tone: 'violet' },
    { label: 'Saved references', value: '—', note: 'Saved references are not tracked', icon: 'notes', tone: 'blue' },
  ]

  return <div className="dashboard-page">
    <section className="dashboard-welcome" aria-labelledby="dashboard-title">
      <div className="dashboard-welcome-copy">
        <span className="dashboard-eyebrow"><span /> Research workspace</span>
        <h2 id="dashboard-title">Explore scientific knowledge.</h2>
        <p>Ask questions across research literature and scientific datasets.</p>
      </div>
      <form className="dashboard-search" onSubmit={submitQuery}>
        <div className="dashboard-search-main">
          <Icon name="search" />
          <label className="sr-only" htmlFor="dashboard-query">Research question</label>
          <textarea id="dashboard-query" value={query} onChange={(event) => setQuery(event.target.value)} rows="1" maxLength={3960} placeholder="Ask a question across papers and datasets…" disabled={loading} onKeyDown={(event) => {
            if (event.key === 'Enter' && !event.shiftKey) {
              event.preventDefault()
              event.currentTarget.form?.requestSubmit()
            }
          }} />
          <button className="dashboard-submit" type="submit" disabled={!query.trim() || loading} aria-label="Start research query">
            {loading ? <span className="dashboard-spinner" /> : <><span>Ask Nerivane</span><Icon name="send" /></>}
          </button>
        </div>
        <div className="dashboard-search-footer">
          <div className="dashboard-source-modes" role="radiogroup" aria-label="Select research sources">
            <span className="source-mode-label">Use</span>
            {sourceModes.map((mode) => <button key={mode.id} className={`source-mode${sourceMode === mode.id ? ' is-selected' : ''}`} type="button" role="radio" aria-checked={sourceMode === mode.id} onClick={() => setSourceMode(mode.id)} disabled={loading}>
              <Icon name={mode.icon} /><span>{mode.label}</span>
            </button>)}
          </div>
          <span className="dashboard-search-hint">Enter to submit · Shift + Enter for a new line</span>
        </div>
      </form>
      <p className="dashboard-routing-note">Your source choice routes this query through the existing research workflow.</p>
    </section>

    <section className="dashboard-suggestions" aria-labelledby="suggestions-title">
      <div className="dashboard-section-heading"><div><span className="dashboard-section-eyebrow">Get started</span><h3 id="suggestions-title">Choose a research direction</h3></div></div>
      <div className="suggestion-grid">
        {suggestions.map((item) => <button className={`suggestion-card tone-${item.tone}`} key={item.title} type="button" onClick={() => onStartResearch(item.query, item.mode)} disabled={loading}>
          <span className="suggestion-card-icon"><Icon name={item.icon} /></span>
          <span className="suggestion-card-copy"><strong>{item.title}</strong><span>{item.description}</span></span>
          <span className="suggestion-card-arrow" aria-hidden="true">↗</span>
        </button>)}
      </div>
    </section>

    <section className="dashboard-stats" aria-label="Workspace statistics">
      {stats.map((stat) => <article className="dashboard-stat-card" key={stat.label}>
        <div className={`dashboard-stat-icon tone-${stat.tone}`}><Icon name={stat.icon} /></div>
        <div className="dashboard-stat-text"><span>{stat.label}</span><strong>{stat.value}</strong><small>{stat.note}</small></div>
      </article>)}
    </section>

    <section className="dashboard-recent" aria-labelledby="recent-conversations-title">
      <div className="dashboard-section-heading recent-heading"><div><span className="dashboard-section-eyebrow">Your activity</span><h3 id="recent-conversations-title">Recent conversations</h3></div><span className="recent-count">{conversations.length}</span></div>
      {conversations.length ? <div className="recent-conversation-list">
        {conversations.slice(0, 5).map((conversation) => <button className="recent-conversation" key={conversation.id} type="button" onClick={() => onOpenConversation(conversation.id)}>
          <span className="recent-conversation-icon"><Icon name="assistant" /></span>
          <span className="recent-conversation-copy"><strong>{conversation.title}</strong><span>{conversationPreview(conversation) || 'No preview available'}</span></span>
          <span className="recent-conversation-time">{relativeTime(conversation.updatedAt || conversation.messages?.at(-1)?.createdAt)}</span>
          <span className="recent-chevron" aria-hidden="true">›</span>
        </button>)}
      </div> : <div className="recent-empty"><span className="recent-empty-icon"><Icon name="assistant" /></span><div><strong>No conversations yet</strong><p>Your recent research sessions will appear here.</p></div></div>}
    </section>
  </div>
}
