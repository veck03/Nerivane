function parseValue(value) {
  if (typeof value !== 'string') return value
  try { return JSON.parse(value) } catch { return value }
}

function getChartData(rawDataOutput) {
  const parsed = parseValue(rawDataOutput)
  if (!Array.isArray(parsed?.tool_outputs)) return []
  return parsed.tool_outputs.flatMap((item) => {
    const result = parseValue(item.output)
    const chart = result && typeof result === 'object' ? result.chart_data : null
    return chart && Array.isArray(chart.labels) && Array.isArray(chart.values)
      ? [{ ...chart, tool: item.tool }]
      : []
  })
}

function formatNumber(value) {
  return new Intl.NumberFormat(undefined, { maximumFractionDigits: 2 }).format(value)
}

function formatAxisLabel(value) {
  if (/^\d{4}-\d{2}-\d{2}$/.test(value)) return `${value.slice(5, 7)}/${value.slice(8)}`
  return String(value)
}

function ChartSvg({ chart }) {
  const values = chart.values.map((value) => (typeof value === 'number' && Number.isFinite(value) ? value : null))
  const valid = values.filter((value) => value !== null)
  if (!valid.length) return <p className="dataset-chart-empty">No valid observations are available to plot.</p>

  const width = 680
  const height = 258
  const left = 62
  const right = 16
  const top = 16
  const bottom = 48
  const plotWidth = width - left - right
  const plotHeight = height - top - bottom
  let minValue = Math.min(...valid)
  let maxValue = Math.max(...valid)
  const valueRange = maxValue - minValue
  const padding = valueRange > 0 ? valueRange * .12 : Math.abs(minValue || 1) * .08
  minValue -= padding
  maxValue += padding
  const x = (index) => left + (values.length <= 1 ? plotWidth / 2 : (index / (values.length - 1)) * plotWidth)
  const barCenter = (index) => left + ((index + .5) / Math.max(values.length, 1)) * plotWidth
  const y = (value) => top + ((maxValue - value) / (maxValue - minValue)) * plotHeight
  const tickValues = Array.from({ length: 5 }, (_, index) => maxValue - ((maxValue - minValue) * index) / 4)
  const tickIndexes = [...new Set([0, Math.round((values.length - 1) / 4), Math.round((values.length - 1) / 2), Math.round((3 * (values.length - 1)) / 4), values.length - 1])]
  const segments = []
  let segment = []
  values.forEach((value, index) => {
    if (value === null) {
      if (segment.length) segments.push(segment)
      segment = []
    } else segment.push(`${segment.length ? 'L' : 'M'} ${x(index)} ${y(value)}`)
  })
  if (segment.length) segments.push(segment)
  const baselineY = y(minValue)
  const slotWidth = plotWidth / Math.max(values.length, 1)
  const barWidth = Math.max(3, Math.min(40, slotWidth * .56))
  const title = chart.title || `${chart.variable || 'Dataset values'} over time`
  const description = `${chart.type === 'bar' ? 'Bar' : 'Line'} chart showing ${chart.variable || 'dataset values'} in ${chart.units || 'the reported units'}.`

  return <svg className="dataset-chart-svg" viewBox={`0 0 ${width} ${height}`} role="img" aria-label={`${title}. ${description}`}>
    <title>{title}</title>
    <desc>{description}</desc>
    {tickValues.map((tick, index) => {
      const tickY = y(tick)
      return <g key={`tick-${index}`}>
        <line x1={left} x2={width - right} y1={tickY} y2={tickY} className="dataset-chart-gridline" />
        <text x={left - 9} y={tickY + 4} textAnchor="end" className="dataset-chart-axis-label">{formatNumber(tick)}</text>
      </g>
    })}
    {chart.type === 'bar' ? values.map((value, index) => {
      if (value === null) return null
      const barY = Math.min(y(value), baselineY)
      const barHeight = Math.max(1, Math.abs(baselineY - y(value)))
      return <rect key={`bar-${index}`} x={barCenter(index) - barWidth / 2} y={barY} width={barWidth} height={barHeight} rx="3" className="dataset-chart-bar">
        <title>{`${chart.labels[index]}: ${formatNumber(value)}${chart.units ? ` ${chart.units}` : ''}`}</title>
      </rect>
    }) : segments.map((path, index) => <path key={`line-${index}`} d={path.join(' ')} className="dataset-chart-line" />)}
    {chart.type !== 'bar' && values.map((value, index) => value === null ? null : <circle key={`point-${index}`} cx={x(index)} cy={y(value)} r={values.length > 40 ? 1.8 : 3} className="dataset-chart-point">
      <title>{`${chart.labels[index]}: ${formatNumber(value)}${chart.units ? ` ${chart.units}` : ''}`}</title>
    </circle>)}
    {tickIndexes.map((index) => {
      const tickX = chart.type === 'bar' ? barCenter(index) : x(index)
      return <text key={`label-${index}`} x={tickX} y={height - 18} textAnchor={index === 0 ? 'start' : index === values.length - 1 ? 'end' : 'middle'} className="dataset-chart-axis-label">{formatAxisLabel(chart.labels[index])}</text>
    })}
    <text x={left} y={height - 2} className="dataset-chart-unit-label">{chart.units || 'Value'}</text>
  </svg>
}

export default function DatasetCharts({ rawDataOutput }) {
  const charts = getChartData(rawDataOutput)
  if (!charts.length) return null
  return <div className="message-charts" aria-label="Charts from ocean dataset results">
    {charts.map((chart, index) => <section className="dataset-chart-card" key={`${chart.tool}-${index}`}>
      <div className="dataset-chart-heading">
        <div><span>Dataset visualization</span><h3>{chart.title || chart.variable}</h3></div>
        {chart.units && <span className="dataset-chart-units">{chart.units}</span>}
      </div>
      <ChartSvg chart={chart} />
      <p className="dataset-chart-footnote">Based on returned dataset values; missing observations are left blank.{chart.type === 'bar' ? ' Y-axis is zoomed to the observed range to show month-to-month differences.' : ''}</p>
    </section>)}
  </div>
}
