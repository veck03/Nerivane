import { useEffect, useRef } from 'react'
import { Icon } from './ApplicationShell.jsx'

const tabs = [
  { id: 'sources', label: 'Sources' },
  { id: 'dataset', label: 'Dataset' },
  { id: 'details', label: 'Details' },
]

function parseValue(value) {
  if (typeof value !== 'string') return value
  try { return JSON.parse(value) } catch { return value }
}

function getToolOutputs(rawDataOutput) {
  const parsed = parseValue(rawDataOutput)
  return Array.isArray(parsed?.tool_outputs)
    ? parsed.tool_outputs.map((item) => ({ ...item, result: parseValue(item.output) }))
    : []
}

function formatValue(value) {
  if (value === null || value === undefined || value === '') return ''
  if (typeof value === 'string') return value
  if (Array.isArray(value)) return value.join(', ')
  if (typeof value === 'object') return Object.entries(value).map(([key, item]) => `${key}: ${formatValue(item)}`).join(' · ')
  return String(value)
}

function DataField({ label, value }) {
  const formatted = formatValue(value)
  if (!formatted) return null
  return <div className="evidence-data-field"><dt>{label}</dt><dd>{formatted}</dd></div>
}

function toolLabel(tool) {
  return ({
    get_monthly_statistics: 'Monthly statistics',
    get_ocean_values_at_point: 'Values at location',
    get_ocean_dataset_info: 'Dataset information',
  })[tool] || tool || 'Dataset tool'
}

function DatasetResults({ message }) {
  if (!message || !['data', 'both'].includes(message.route)) {
    return <div className="evidence-empty"><span className="evidence-empty-mark">∅</span><strong>No dataset accessed</strong><p>This answer did not use the ocean dataset.</p></div>
  }
  if (message.rawDataOutput == null) return <div className="evidence-empty"><span className="evidence-empty-mark">∅</span><strong>No dataset results returned</strong><p>The dataset source was selected, but no dataset information was returned for this answer.</p></div>

  const parsed = parseValue(message.rawDataOutput)
  const outputs = getToolOutputs(message.rawDataOutput)
  if (!outputs.length) {
    return <div className="dataset-results">
      <p className="evidence-intro">The backend returned dataset output, but it did not include structured tool results.</p>
      <pre className="dataset-raw-output">{typeof parsed === 'string' ? parsed : JSON.stringify(parsed, null, 2)}</pre>
    </div>
  }

  return <div className="dataset-results">
    {outputs.map((item, index) => {
      const result = item.result && typeof item.result === 'object' ? item.result : {}
      const variables = new Set()
      if (item.arguments?.variable) variables.add(item.arguments.variable)
      if (result.values && typeof result.values === 'object') Object.keys(result.values).forEach((name) => variables.add(name))
      const describedVariables = result.variables && typeof result.variables === 'object' ? Object.entries(result.variables) : []
      const units = result.units
        || (result.values ? Object.entries(result.values).map(([name, value]) => value?.units && `${name}: ${value.units}`).filter(Boolean).join(' · ') : '')
        || describedVariables.map(([name, value]) => value?.units && `${name}: ${value.units}`).filter(Boolean).join(' · ')
      const measurements = ['mean', 'minimum', 'maximum', 'standard_deviation']
        .filter((key) => result[key] != null)
        .map((key) => `${key.replaceAll('_', ' ')}: ${result[key]}`)
      if (result.values && typeof result.values === 'object') {
        Object.entries(result.values).forEach(([name, value]) => {
          if (value && typeof value === 'object' && value.value != null) measurements.push(`${name}: ${value.value}${value.units ? ` ${value.units}` : ''}`)
        })
      }
      const coverage = [
        result.period && `Period ${result.period}`,
        result.date && `Date ${result.date}`,
        result.time_start && `From ${result.time_start}`,
        result.time_end && `To ${result.time_end}`,
        result.selected_grid_point && `Selected grid point ${formatValue(result.selected_grid_point)}`,
        result.requested_point && `Requested point ${formatValue(result.requested_point)}`,
        result.latitude_range && `Latitude ${formatValue(result.latitude_range)}`,
        result.longitude_range && `Longitude ${formatValue(result.longitude_range)}`,
        result.selected_depth_m != null && `Depth ${result.selected_depth_m} m`,
        result.depth_levels_m?.length && `Depth levels ${formatValue(result.depth_levels_m)} m`,
      ].filter(Boolean).join(' · ')

      return <article className="dataset-result-card" key={`${item.tool}-${index}`}>
        <div className="dataset-result-heading"><span className="dataset-tool-mark"><Icon name="datasets" /></span><div><strong>{toolLabel(item.tool)}</strong>{result.dataset && <small>{result.dataset}</small>}</div></div>
        <dl className="evidence-data-grid">
          <DataField label={variables.size ? 'Variables accessed' : 'Variables described'} value={variables.size ? [...variables].join(', ') : describedVariables.map(([name]) => name).join(', ')} />
          <DataField label="Records / observations" value={result.valid_observation_count} />
          {result.time_steps != null && <DataField label="Time steps described" value={result.time_steps} />}
          <DataField label="Units" value={units} />
          <DataField label="Returned measurements" value={measurements.length ? measurements.join(' · ') : undefined} />
          <DataField label="Spatial / temporal coverage" value={coverage} />
          <DataField label="Aggregation" value={result.aggregation_scope || result.mean_method} />
          <DataField label="Missing values" value={result.nan_values_skipped === true ? 'NaN values skipped' : undefined} />
        </dl>
        {item.arguments && Object.keys(item.arguments).length > 0 && <details className="evidence-parameters">
          <summary>Query parameters / filters</summary>
          <dl className="evidence-parameter-list">{Object.entries(item.arguments).map(([key, value]) => <DataField key={key} label={key.replaceAll('_', ' ')} value={value} />)}</dl>
        </details>}
        <details className="evidence-raw-details">
          <summary>Returned result</summary>
          <pre className="dataset-raw-output">{typeof item.result === 'string' ? item.result : JSON.stringify(item.result, null, 2)}</pre>
        </details>
      </article>
    })}
  </div>
}

function SourceResults({ message, selectedSourceId, selectedChunkIndex, citationRequestId, onSelectSource, active }) {
  const panelContentRef = useRef(null)
  const sources = message?.paperSources || []

  useEffect(() => {
    if (!active || !selectedSourceId || selectedChunkIndex == null || !panelContentRef.current) return
    const sourceCard = panelContentRef.current.querySelector(`[data-source-id="${selectedSourceId}"]`)
    const chunk = sourceCard?.querySelector(`[data-chunk-index="${selectedChunkIndex}"]`)
    if (!sourceCard || !chunk) return
    chunk.open = true
    chunk.classList.add('is-highlighted')
    chunk.scrollIntoView({ behavior: 'smooth', block: 'nearest' })
    const timer = window.setTimeout(() => chunk.classList.remove('is-highlighted'), 2400)
    return () => window.clearTimeout(timer)
  }, [active, citationRequestId, message?.messageId, selectedSourceId, selectedChunkIndex])

  if (!sources.length) return <div className="evidence-empty"><span className="evidence-empty-mark">∅</span><strong>No paper sources</strong><p>This answer did not retrieve research papers.</p></div>

  return <div className="evidence-panel-content source-evidence-content" ref={panelContentRef}>
    <div className="evidence-section-heading"><div><strong>Research papers</strong><span>{sources.length} {sources.length === 1 ? 'source' : 'sources'} used in this answer</span></div><span className="evidence-count">{sources.length}</span></div>
    <div className="evidence-source-list">
      {sources.map((source) => {
        const selected = source.source_id === selectedSourceId
        const chunks = source.excerpts || []
        const doiHref = source.doi_url || source.paper_url || (source.doi ? `https://doi.org/${source.doi.replace(/^https?:\/\/(dx\.)?doi\.org\//i, '')}` : '')
        return <article className={`evidence-source-card${selected ? ' is-selected' : ''}`} data-source-id={source.source_id} key={`${message?.messageId}-${source.source_id}`}>
          <button className="evidence-source-select" type="button" aria-expanded={selected} onClick={() => onSelectSource(source)}>
            <span className="evidence-source-chevron" aria-hidden="true">⌄</span>
            <span className="evidence-source-copy"><strong title={source.title}>{source.title}</strong><span>{source.authors || 'Unknown author'}{source.publication_year ? ` · ${source.publication_year}` : ''}</span></span>
            {source.cited && <span className="evidence-cited-tag">Cited</span>}
          </button>
          {selected && <div className="evidence-source-body">
            {(source.venue || source.pages?.length > 0) && <div className="evidence-source-meta">{[source.venue, source.pages?.length ? `Pages ${source.pages.join(', ')}` : ''].filter(Boolean).join(' · ')}</div>}
            {source.doi && doiHref && <a className="evidence-doi-link" href={doiHref} target="_blank" rel="noreferrer">DOI: {source.doi}<span aria-hidden="true">↗</span></a>}
            {!source.doi && source.paper_url && <a className="evidence-doi-link" href={source.paper_url} target="_blank" rel="noreferrer">Open paper<span aria-hidden="true">↗</span></a>}
            {chunks.length > 0 ? <div className="evidence-chunk-list" aria-label={`Retrieved chunks from ${source.title}`}>
              {chunks.map((chunk, chunkIndex) => <details className="evidence-chunk" data-chunk-index={chunkIndex} key={`${message?.messageId}-${source.source_id}-chunk-${chunkIndex}`}>
                <summary><span>Retrieved chunk {chunkIndex + 1}</span>{chunk.page_number != null && <span>Page {chunk.page_number}</span>}</summary>
                <p>{chunk.text}</p>
              </details>)}
            </div> : <p className="evidence-no-chunks">No retrieved excerpts were returned for this paper.</p>}
          </div>}
        </article>
      })}
    </div>
  </div>
}

function OperationDetails({ message }) {
  if (!message) return <div className="evidence-empty"><span className="evidence-empty-mark">i</span><strong>No active research operation</strong><p>Operation details will appear here after an answer is received.</p></div>
  const sources = message.paperSources || []
  const outputs = getToolOutputs(message.rawDataOutput)
  const status = Object.keys(message.sourceErrors || {}).length ? 'Partial · one or more sources reported an error' : message.failed ? 'Failed' : 'Completed'
  return <div className="evidence-panel-content details-evidence-content">
    <div className="evidence-detail-block"><span className="evidence-detail-label">Processing status</span><strong className={`operation-status${message.failed || Object.keys(message.sourceErrors || {}).length ? ' is-partial' : ''}`}><span />{status}</strong></div>
    <div className="evidence-detail-block"><span className="evidence-detail-label">Selected sources</span><strong>{routeLabelsForEvidence(message.route)}</strong><p>{sources.length ? `${sources.length} paper sources returned` : 'No paper sources returned'}</p></div>
    <div className="evidence-detail-block"><span className="evidence-detail-label">Paper retrieval</span><strong>{(message.paperChunks || []).length} retrieved {(message.paperChunks || []).length === 1 ? 'chunk' : 'chunks'}</strong><p>{sources.length} grouped {(sources.length === 1) ? 'paper' : 'papers'}</p></div>
    <div className="evidence-detail-block"><span className="evidence-detail-label">Dataset access</span><strong>{outputs.length ? `${outputs.length} dataset ${outputs.length === 1 ? 'tool' : 'tools'} returned results` : 'No dataset tool results'}</strong>{outputs.length > 0 && <p>{outputs.map((item) => toolLabel(item.tool)).join(' · ')}</p>}</div>
    {message.claimCheckStatus && message.claimCheckStatus !== 'not_requested' && <div className="evidence-detail-block"><span className="evidence-detail-label">Claim support check</span><strong>{message.claimCheckStatus.replaceAll('_', ' ')}</strong>{message.claimChecks?.length > 0 && <p>{message.claimChecks.length} findings</p>}</div>}
    {Object.keys(message.sourceErrors || {}).length > 0 && <p className="evidence-partial-note">Some source retrieval did not complete. Error details are not shown here.</p>}
  </div>
}

function routeLabelsForEvidence(route) {
  return ({ data: 'Ocean dataset', paper: 'Research papers', both: 'Ocean dataset + research papers', none: 'General answer' })[route] || 'Not available'
}

export default function EvidenceInspector({ open, activeTab, onSelectTab, onClose, message, selectedSourceId, selectedChunkIndex, citationRequestId, onSelectSource, onCopyReferences, onDownloadBibtex, copiedMessage }) {
  return <>
    <button className={`evidence-drawer-scrim${open ? ' is-visible' : ''}`} type="button" aria-label="Close evidence inspector" onClick={onClose} />
    <aside id="evidence-inspector" className={`evidence-inspector${open ? ' is-open' : ''}`} aria-label="Evidence inspector" aria-hidden={!open}>
      <div className="evidence-inspector-header">
        <div><span className="evidence-header-eyebrow">Context</span><h2>Evidence inspector</h2></div>
        <div className="evidence-header-actions">
          {activeTab === 'sources' && message?.paperSources?.length > 0 && <>
            <button type="button" className="evidence-text-action" onClick={onCopyReferences}>{copiedMessage === message.messageId ? 'Copied' : 'Copy refs'}</button>
            <button type="button" className="evidence-text-action" onClick={() => onDownloadBibtex(message.paperSources)}>BibTeX</button>
          </>}
          <button className="icon-button evidence-close" type="button" aria-label="Close evidence inspector" onClick={onClose}><Icon name="close" /></button>
        </div>
      </div>
      <div className="evidence-tabs" role="tablist" aria-label="Evidence categories">
        {tabs.map((tab) => <button key={tab.id} type="button" role="tab" id={`evidence-tab-${tab.id}`} aria-selected={activeTab === tab.id} aria-controls="evidence-tab-panel" className={`evidence-tab${activeTab === tab.id ? ' is-active' : ''}`} onClick={() => onSelectTab(tab.id)}>{tab.label}</button>)}
      </div>
      <div className="evidence-tab-panel" id="evidence-tab-panel" role="tabpanel" aria-labelledby={`evidence-tab-${activeTab}`}>
        <div hidden={activeTab !== 'sources'}><SourceResults active={activeTab === 'sources'} message={message} selectedSourceId={selectedSourceId} selectedChunkIndex={selectedChunkIndex} citationRequestId={citationRequestId} onSelectSource={onSelectSource} /></div>
        <div hidden={activeTab !== 'dataset'}><DatasetResults message={message} /></div>
        <div hidden={activeTab !== 'details'}><OperationDetails message={message} /></div>
      </div>
    </aside>
  </>
}
