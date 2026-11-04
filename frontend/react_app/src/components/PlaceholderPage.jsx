import { Icon } from './ApplicationShell.jsx'

const descriptions = {
  '/dashboard': ['Your research overview will live here.', 'A workspace for recent activity, saved research, and dataset status.'],
  '/papers': ['Your paper library is ready for the next phase.', 'Indexed papers and saved references will appear here when library browsing is implemented.'],
  '/datasets': ['Explore your research datasets.', 'Dataset browsing and summaries will be added here in a later phase.'],
  '/visualizations': ['See research data in context.', 'Charts and geographical views will be added here as visualization features are developed.'],
  '/projects': ['Organize research by project.', 'Project workspaces and their saved materials will be introduced in a later phase.'],
  '/shared': ['Collaborate on research.', 'Shared workspaces are not connected yet.'],
  '/notes': ['Keep research notes together.', 'Notes are not connected to a storage feature yet.'],
  '/settings': ['Workspace preferences.', 'Settings will become available as configurable options are introduced.'],
  '/about': ['About Nerivane.', 'Nerivane is an AI research assistant for exploring scientific papers and ocean datasets.'],
}

export default function PlaceholderPage({ path }) {
  const [title, description] = descriptions[path] || ['Page not found.', 'Choose a destination from the navigation.']
  return <section className="placeholder-page" aria-labelledby="placeholder-title">
    <div className="placeholder-card">
      <div className="placeholder-icon"><Icon name={path === '/datasets' || path === '/visualizations' ? 'datasets' : 'papers'} /></div>
      <span className="placeholder-eyebrow">Workspace section</span>
      <h2 id="placeholder-title">{title}</h2>
      <p>{description}</p>
      <span className="placeholder-status">Coming in a future phase</span>
    </div>
  </section>
}
