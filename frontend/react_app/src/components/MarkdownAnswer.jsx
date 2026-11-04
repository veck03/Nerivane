import { Fragment } from 'react'

const citationPattern = /^\[(S\d+|\d+)(?:,\s*p\.?\s*(\d+))?\]$/i
const tableDivider = /^\s*\|?\s*:?-{3,}:?\s*(?:\|\s*:?-{3,}:?\s*)+\|?\s*$/

function resolveCitation(marker, sources) {
  const match = marker.match(citationPattern)
  if (!match) return null
  const sourceId = /^S/i.test(match[1]) ? match[1].toUpperCase() : `S${match[1]}`
  const source = sources.find((item) => item.source_id?.toUpperCase() === sourceId)
  return source ? { source, page: match[2] ? Number(match[2]) : null } : null
}

function safeHref(value) {
  try {
    const url = new URL(value, window.location.origin)
    return ['http:', 'https:', 'mailto:'].includes(url.protocol) ? url.href : null
  } catch {
    return null
  }
}

function renderInline(text, sources, onCitationClick, keyPrefix, messageId) {
  const tokenPattern = /(\[(?:S\d+|\d+)(?:,\s*p\.?\s*\d+)?\]|\[(?:[^\]]+)\]\([^)]+\)|`[^`]+`|\*\*[^*]+\*\*|__[^_]+__|~~[^~]+~~|(?<!\*)\*[^*\n]+\*(?!\*)|(?<!_)_[^_\n]+_(?!_))/gi
  const parts = text.split(tokenPattern)
  return parts.map((part, index) => {
    const key = `${keyPrefix}-${index}`
    const citation = resolveCitation(part, sources)
    if (citation) return <a className="inline-citation" href={`#source-${messageId}-${citation.source.source_id}`} key={key} title={`Inspect ${citation.source.title}${citation.page ? `, page ${citation.page}` : ''}`} onClick={(event) => { event.preventDefault(); onCitationClick(citation.source, citation.page, messageId) }}>{part}</a>

    const link = part.match(/^\[([^\]]+)\]\(([^)]+)\)$/)
    if (link) {
      const href = safeHref(link[2])
      return href ? <a href={href} key={key} target={href.startsWith('http') ? '_blank' : undefined} rel={href.startsWith('http') ? 'noreferrer' : undefined}>{link[1]}</a> : link[1]
    }
    if (part.startsWith('`') && part.endsWith('`')) return <code key={key}>{part.slice(1, -1)}</code>
    if ((part.startsWith('**') && part.endsWith('**')) || (part.startsWith('__') && part.endsWith('__'))) return <strong key={key}>{part.slice(2, -2)}</strong>
    if (part.startsWith('~~') && part.endsWith('~~')) return <del key={key}>{part.slice(2, -2)}</del>
    if ((part.startsWith('*') && part.endsWith('*')) || (part.startsWith('_') && part.endsWith('_'))) return <em key={key}>{part.slice(1, -1)}</em>
    return <Fragment key={key}>{part}</Fragment>
  })
}

function isBlockStart(lines, index) {
  const line = lines[index]
  if (/^\s*(```|~~~)/.test(line) || /^\s{0,3}#{1,6}\s/.test(line) || /^\s{0,3}>/.test(line) || /^\s*([-*_]\s*){3,}$/.test(line)) return true
  if (/^\s*([-+*]|\d+[.)])\s+/.test(line)) return true
  return Boolean(lines[index + 1] && line.includes('|') && tableDivider.test(lines[index + 1]))
}

function splitTableRow(line) {
  return line.trim().replace(/^\|/, '').replace(/\|$/, '').split(/(?<!\\)\|/).map((cell) => cell.replace(/\\\|/g, '|').trim())
}

export default function MarkdownAnswer({ text, sources, onCitationClick, messageId }) {
  const lines = (text || '').replace(/\r\n?/g, '\n').split('\n')
  const blocks = []
  let index = 0

  while (index < lines.length) {
    const line = lines[index]
    if (!line.trim()) { index += 1; continue }

    const fence = line.match(/^\s*(```|~~~)([^\s]*)\s*$/)
    if (fence) {
      const codeLines = []
      index += 1
      while (index < lines.length && !new RegExp(`^\\s*${fence[1]}\\s*$`).test(lines[index])) codeLines.push(lines[index++])
      if (index < lines.length) index += 1
      blocks.push(<pre className="answer-code" key={`block-${blocks.length}`}><code className={fence[2] ? `language-${fence[2]}` : undefined}>{codeLines.join('\n')}</code></pre>)
      continue
    }

    const heading = line.match(/^\s{0,3}(#{1,6})\s+(.+?)\s*#*\s*$/)
    if (heading) {
      const Heading = `h${heading[1].length}`
      blocks.push(<Heading key={`block-${blocks.length}`}>{renderInline(heading[2], sources, onCitationClick, `h-${blocks.length}`, messageId)}</Heading>)
      index += 1
      continue
    }

    if (index + 1 < lines.length && line.includes('|') && tableDivider.test(lines[index + 1])) {
      const headers = splitTableRow(line)
      index += 2
      const rows = []
      while (index < lines.length && lines[index].trim() && lines[index].includes('|')) rows.push(splitTableRow(lines[index++]))
      blocks.push(<div className="answer-table-scroll" key={`block-${blocks.length}`}><table className="answer-table"><thead><tr>{headers.map((cell, cellIndex) => <th key={cellIndex}>{renderInline(cell, sources, onCitationClick, `th-${cellIndex}`, messageId)}</th>)}</tr></thead><tbody>{rows.map((row, rowIndex) => <tr key={rowIndex}>{headers.map((_, cellIndex) => <td key={cellIndex}>{renderInline(row[cellIndex] || '', sources, onCitationClick, `td-${rowIndex}-${cellIndex}`, messageId)}</td>)}</tr>)}</tbody></table></div>)
      continue
    }

    if (/^\s*([-*_]\s*){3,}$/.test(line)) {
      blocks.push(<hr key={`block-${blocks.length}`} />)
      index += 1
      continue
    }

    if (/^\s{0,3}>/.test(line)) {
      const quoteLines = []
      while (index < lines.length && /^\s{0,3}>/.test(lines[index])) quoteLines.push(lines[index++].replace(/^\s{0,3}>\s?/, ''))
      blocks.push(<blockquote key={`block-${blocks.length}`}><p>{renderInline(quoteLines.join(' '), sources, onCitationClick, `q-${blocks.length}`, messageId)}</p></blockquote>)
      continue
    }

    const listStart = line.match(/^\s{0,3}([-+*]|\d+[.)])\s+(.+)$/)
    if (listStart) {
      const ordered = /^\d/.test(listStart[1])
      const List = ordered ? 'ol' : 'ul'
      const items = []
      while (index < lines.length) {
        const item = lines[index].match(/^\s{0,3}([-+*]|\d+[.)])\s+(.+)$/)
        if (!item || /^\d/.test(item[1]) !== ordered) break
        items.push(item[2])
        index += 1
      }
      blocks.push(<List key={`block-${blocks.length}`}>{items.map((item, itemIndex) => <li key={itemIndex}>{renderInline(item, sources, onCitationClick, `li-${blocks.length}-${itemIndex}`, messageId)}</li>)}</List>)
      continue
    }

    const paragraph = [line.trim()]
    index += 1
    while (index < lines.length && lines[index].trim() && !isBlockStart(lines, index)) paragraph.push(lines[index++].trim())
    blocks.push(<p key={`block-${blocks.length}`}>{renderInline(paragraph.join(' '), sources, onCitationClick, `p-${blocks.length}`, messageId)}</p>)
  }

  return <div className="markdown-answer">{blocks}</div>
}
