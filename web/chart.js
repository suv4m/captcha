/**
 * Lightweight SVG Chart Helper for Lab visualizations.
 * Offline, vanilla, zero external dependencies.
 */

export function renderLineChart(container, { data, xKey, yKey, title, xLabel, yLabel, minX = 0, maxX = 1, minY = 0, maxY = 1 }) {
  const w = 480;
  const h = 260;
  const pad = { top: 30, right: 20, bottom: 40, left: 50 };
  const plotW = w - pad.left - pad.right;
  const plotH = h - pad.top - pad.bottom;

  const points = data.map(d => {
    const x = pad.left + ((d[xKey] - minX) / (maxX - minX)) * plotW;
    const y = pad.top + plotH - ((d[yKey] - minY) / (maxY - minY)) * plotH;
    return `${x.toFixed(1)},${y.toFixed(1)}`;
  });

  const pathD = "M " + points.join(" L ");

  container.innerHTML = `
    <div style="font-weight: 600; font-size: 13px; margin-bottom: 6px;">${title}</div>
    <svg viewBox="0 0 ${w} ${h}" width="100%" height="${h}" style="overflow: visible; font-family: var(--font-sans); font-size: 11px;">
      <!-- Grid lines -->
      <line x1="${pad.left}" y1="${pad.top}" x2="${pad.left}" y2="${pad.top + plotH}" stroke="var(--border)" stroke-width="1" />
      <line x1="${pad.left}" y1="${pad.top + plotH}" x2="${pad.left + plotW}" y2="${pad.top + plotH}" stroke="var(--border)" stroke-width="1" />
      <line x1="${pad.left}" y1="${pad.top + plotH/2}" x2="${pad.left + plotW}" y2="${pad.top + plotH/2}" stroke="var(--border)" stroke-dasharray="3,3" stroke-width="1" />

      <!-- Diagonal reference if ROC -->
      ${minX === 0 && maxX === 1 && minY === 0 && maxY === 1 ? `
        <line x1="${pad.left}" y1="${pad.top + plotH}" x2="${pad.left + plotW}" y2="${pad.top}" stroke="var(--muted)" stroke-dasharray="4,4" stroke-width="1" opacity="0.6"/>
      ` : ''}

      <!-- Curve -->
      <path d="${pathD}" fill="none" stroke="var(--accent)" stroke-width="2.5" />

      <!-- Labels -->
      <text x="${pad.left}" y="${pad.top - 10}" fill="var(--muted)">${yLabel || yKey} (${maxY})</text>
      <text x="${pad.left}" y="${pad.top + plotH + 20}" fill="var(--muted)">${minX}</text>
      <text x="${pad.left + plotW}" y="${pad.top + plotH + 20}" text-anchor="end" fill="var(--muted)">${maxX}</text>
      <text x="${pad.left + plotW/2}" y="${pad.top + plotH + 34}" text-anchor="middle" fill="var(--muted)">${xLabel || xKey}</text>
    </svg>
  `;
}

export function renderBarChart(container, { data, labelKey, valueKey, title, maxVal, unit = "%" }) {
  const w = 480;
  const barHeight = 24;
  const gap = 12;
  const padLeft = 140;
  const padRight = 50;
  const plotW = w - padLeft - padRight;
  const h = data.length * (barHeight + gap) + 40;

  const actualMax = maxVal || Math.max(...data.map(d => d[valueKey]), 0.01);

  const bars = data.map((d, i) => {
    const y = 30 + i * (barHeight + gap);
    const barW = Math.max(2, (d[valueKey] / actualMax) * plotW);
    const isSpecial = d.highlight;
    const barColor = isSpecial ? "var(--danger)" : "var(--accent)";
    const displayVal = typeof d[valueKey] === "number" ? (d[valueKey] * (unit === "%" ? 100 : 1)).toFixed(1) + unit : d[valueKey];

    return `
      <g>
        <text x="${padLeft - 10}" y="${y + barHeight/2 + 4}" text-anchor="end" fill="var(--text)" font-size="12px">${d[labelKey]}</text>
        <rect x="${padLeft}" y="${y}" width="${barW}" height="${barHeight}" rx="4" fill="${barColor}" />
        <text x="${padLeft + barW + 8}" y="${y + barHeight/2 + 4}" fill="var(--muted)" font-size="11px">${displayVal}</text>
      </g>
    `;
  }).join("");

  container.innerHTML = `
    <div style="font-weight: 600; font-size: 13px; margin-bottom: 6px;">${title}</div>
    <svg viewBox="0 0 ${w} ${h}" width="100%" height="${h}" style="font-family: var(--font-sans);">
      ${bars}
    </svg>
  `;
}

