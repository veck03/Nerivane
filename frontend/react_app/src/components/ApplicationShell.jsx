import { useState } from 'react'
import './application-shell.css'

const mainNavigation = [
  { label: 'Dashboard', path: '/dashboard', icon: 'dashboard' },
  { label: 'Research Assistant', path: '/', icon: 'assistant' },
  { label: 'Paper Library', path: '/papers', icon: 'papers' },
  { label: 'Datasets', path: '/datasets', icon: 'datasets' },
  { label: 'Visualizations', path: '/visualizations', icon: 'visualizations' },
]

const workspaceNavigation = [
  { label: 'Projects', path: '/projects', icon: 'projects' },
  { label: 'Shared Research', path: '/shared', icon: 'shared' },
  { label: 'Notes', path: '/notes', icon: 'notes' },
]

const bottomNavigation = [
  { label: 'Settings', path: '/settings', icon: 'settings' },
  { label: 'About Developer', path: '/about', icon: 'about' },
]

const pageTitles = {
  '/': 'Research Assistant',
  '/dashboard': 'Dashboard',
  '/papers': 'Paper Library',
  '/datasets': 'Datasets',
  '/visualizations': 'Visualizations',
  '/projects': 'Projects',
  '/shared': 'Shared Research',
  '/notes': 'Notes',
  '/settings': 'Settings',
  '/about': 'About Developer',
}

const iconPaths = {
  dashboard: <><rect x="3.5" y="3.5" width="7" height="7" rx="1.5" /><rect x="13.5" y="3.5" width="7" height="4" rx="1.5" /><rect x="13.5" y="10.5" width="7" height="10" rx="1.5" /><rect x="3.5" y="13.5" width="7" height="7" rx="1.5" /></>,
  assistant: <><path d="M12 3.5a7.5 7.5 0 0 0-6.5 11.25L4 20l5.25-1.5A7.5 7.5 0 1 0 12 3.5Z" /><path d="M9 12h.01M12 12h.01M15 12h.01" /></>,
  papers: <><path d="M7 3.5h7l4 4V20a1.5 1.5 0 0 1-1.5 1.5h-9A1.5 1.5 0 0 1 6 20V5a1.5 1.5 0 0 1 1-1.5Z" /><path d="M14 4v4h4M9 12h6M9 16h6" /></>,
  datasets: <><ellipse cx="12" cy="5" rx="8" ry="3" /><path d="M4 5v7c0 1.66 3.58 3 8 3s8-1.34 8-3V5M4 12v7c0 1.66 3.58 3 8 3s8-1.34 8-3v-7" /></>,
  visualizations: <><path d="M4 19.5h16M5.5 17V10M10 17V5M14.5 17v-4M19 17V8" /></>,
  projects: <><path d="M3.5 7A1.5 1.5 0 0 1 5 5.5h5l2 2h7A1.5 1.5 0 0 1 20.5 9v9a1.5 1.5 0 0 1-1.5 1.5H5A1.5 1.5 0 0 1 3.5 18Z" /></>,
  shared: <><circle cx="9" cy="8" r="3" /><path d="M3.5 19a5.5 5.5 0 0 1 11 0M16 5.5a3 3 0 0 1 0 5.8M17 14a5 5 0 0 1 3.5 4.8" /></>,
  notes: <><path d="M6 3.5h12A1.5 1.5 0 0 1 19.5 5v11l-5 5h-8A1.5 1.5 0 0 1 5 19.5v-14A2 2 0 0 1 6 3.5Z" /><path d="M14 20.5V16h5M8.5 8.5h7M8.5 12h7" /></>,
  settings: <><circle cx="12" cy="12" r="3" /><path d="M19.4 13.5a7.4 7.4 0 0 0 0-3l1.4-1.1-1.5-2.6-1.7.6a7.4 7.4 0 0 0-2.6-1.5L14.7 4h-3.1l-.3 1.9a7.4 7.4 0 0 0-2.6 1.5L7 6.8 5.5 9.4l1.4 1.1a7.4 7.4 0 0 0 0 3l-1.4 1.1L7 17.2l1.7-.6a7.4 7.4 0 0 0 2.6 1.5l.3 1.9h3.1l.3-1.9a7.4 7.4 0 0 0 2.6-1.5l1.7.6 1.5-2.6Z" transform="translate(-1 -1)" /></>,
  about: <><circle cx="12" cy="12" r="9" /><path d="M9.8 9a2.3 2.3 0 1 1 4.3 1.2c-.8 1.1-2.1 1.3-2.1 3M12 16.8h.01" /></>,
  menu: <><path d="M4 6h16M4 12h16M4 18h16" /></>,
  collapse: <><rect x="3.5" y="4" width="17" height="16" rx="2" /><path d="M9 4v16M14 9l-3 3 3 3" /></>,
  expand: <><rect x="3.5" y="4" width="17" height="16" rx="2" /><path d="M9 4v16M13 9l3 3-3 3" /></>,
  search: <><circle cx="10.8" cy="10.8" r="6.3" /><path d="m16 16 4.5 4.5" /></>,
  plus: <><path d="M12 5v14M5 12h14" /></>,
  close: <><path d="m6 6 12 12M18 6 6 18" /></>,
  send: <><path d="m21 3-7.2 18-3.7-7.1L3 10.2 21 3Z" /><path d="m10.1 13.9 4.1-4.1" /></>,
}

export function Icon({ name, className = '' }) {
  return <svg className={className} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.7" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">{iconPaths[name] || iconPaths.papers}</svg>
}

function NavigationGroup({ title, items, currentPath, navigate, collapsed, onNavigate }) {
  return (
    <div className="sidebar-group">
      {!collapsed && <div className="sidebar-section-label">{title}</div>}
      <nav aria-label={title} className="sidebar-nav">
        {items.map((item) => {
          const active = currentPath === item.path
          return <a key={item.path} className={`sidebar-link${active ? ' is-active' : ''}`} href={item.path} aria-current={active ? 'page' : undefined} title={collapsed ? item.label : undefined} onClick={(event) => { event.preventDefault(); navigate(item.path); onNavigate?.() }}>
            <Icon name={item.icon} />{!collapsed && <span>{item.label}</span>}
          </a>
        })}
      </nav>
    </div>
  )
}

export default function ApplicationShell({ children, currentPath, navigate, collapsed, onToggleCollapsed, mobileOpen, onToggleMobile, onCloseMobile, conversations, activeConversationId, onNewChat, onSelectConversation, busy }) {
  const [conversationSearch, setConversationSearch] = useState('')
  const pageTitle = pageTitles[currentPath] || 'Workspace'
  const filteredConversations = conversations.filter((conversation) => conversation.title.toLowerCase().includes(conversationSearch.trim().toLowerCase()))

  return <div className={`application-layout${collapsed ? ' sidebar-collapsed' : ''}${mobileOpen ? ' mobile-sidebar-open' : ''}`}>
    <button className="sidebar-scrim" type="button" aria-label="Close navigation" onClick={onCloseMobile} />
    <aside className="app-sidebar" aria-label="Main navigation">
      <div className="sidebar-brand-row">
        <a className="sidebar-brand" href="/" aria-label={collapsed ? 'Expand sidebar' : 'Nerivane home'} title={collapsed ? 'Expand sidebar' : undefined} onClick={(event) => { event.preventDefault(); if (collapsed) { onToggleCollapsed(); return } navigate('/'); onCloseMobile() }}>
          <span className="nerivane-mark" aria-hidden="true"><span /></span>{!collapsed && <span className="sidebar-brand-name">Nerivane</span>}
        </a>
        <button className="icon-button sidebar-close" type="button" aria-label="Close navigation" onClick={onCloseMobile}><Icon name="close" /></button>
        <button className="icon-button collapse-button" type="button" aria-label={collapsed ? 'Expand sidebar' : 'Collapse sidebar'} title={collapsed ? 'Expand sidebar' : 'Collapse sidebar'} onClick={onToggleCollapsed}><Icon name={collapsed ? 'expand' : 'collapse'} /></button>
      </div>
      <div className="sidebar-scroll-area">
        <button className="new-chat-button" type="button" onClick={onNewChat} title={collapsed ? 'New chat' : undefined} disabled={busy}><Icon name="plus" />{!collapsed && <span>New Chat</span>}</button>
        <NavigationGroup title="Main" items={mainNavigation} currentPath={currentPath} navigate={navigate} collapsed={collapsed} onNavigate={onCloseMobile} />
        <NavigationGroup title="Workspace" items={workspaceNavigation} currentPath={currentPath} navigate={navigate} collapsed={collapsed} onNavigate={onCloseMobile} />
        {!collapsed && <section className="conversation-history" aria-label="Recent conversations">
          <div className="history-heading"><span className="sidebar-section-label">History</span><span className="history-count">{conversations.length || ''}</span></div>
          <label className="conversation-search"><Icon name="search" /><span className="sr-only">Search conversations</span><input value={conversationSearch} onChange={(event) => setConversationSearch(event.target.value)} placeholder="Search conversations" />{conversationSearch && <button type="button" aria-label="Clear search" onClick={() => setConversationSearch('')}><Icon name="close" /></button>}</label>
          <div className="conversation-list">
            {filteredConversations.map((conversation) => <button key={conversation.id} className={`conversation-link${activeConversationId === conversation.id && currentPath === '/' ? ' is-current' : ''}`} type="button" disabled={busy} onClick={() => { onSelectConversation(conversation.id); onCloseMobile() }} title={conversation.title}><span className="conversation-indicator" /><span>{conversation.title}</span></button>)}
            {filteredConversations.length === 0 && <p className="history-empty">{conversationSearch ? 'No matching conversations' : 'Your recent chats will appear here'}</p>}
          </div>
        </section>}
      </div>
      <div className="sidebar-bottom">
        <NavigationGroup title="Account" items={bottomNavigation} currentPath={currentPath} navigate={navigate} collapsed={collapsed} onNavigate={onCloseMobile} />
        {!collapsed && <div className="sidebar-footer-note"><span className="footer-avatar">N</span><span><strong>Nerivane</strong><small>Research workspace</small></span></div>}
      </div>
    </aside>
    <div className="workspace-area">
      {currentPath !== '/' && <header className="workspace-topbar">
        <button className="icon-button mobile-menu-button" type="button" aria-label="Open navigation" onClick={onToggleMobile}><Icon name="menu" /></button>
        <div className="topbar-heading"><span className="topbar-kicker">Nerivane workspace</span><h1>{pageTitle}</h1></div>
        <div className="topbar-status"><span className="status-dot" /><span>Research assistant</span></div>
      </header>}
      <main className={`workspace-content${currentPath === '/' ? ' workspace-content-chat' : ''}`}>{children}</main>
    </div>
  </div>
}
