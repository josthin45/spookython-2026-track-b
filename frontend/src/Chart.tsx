type Series = {
  name: string;
  color: string;
  values: number[];
};

type Band = {
  low: number[];
  high: number[];
  color: string;
};

type ChartProps = {
  title: string;
  days: number[];
  series: Series[];
  band?: Band;
};

export function Chart({ title, days, series, band }: ChartProps) {
  const width = 640;
  const height = 280;
  const pad = { top: 16, right: 16, bottom: 32, left: 44 };
  const innerW = width - pad.left - pad.right;
  const innerH = height - pad.top - pad.bottom;
  const flat = series.flatMap((item) => item.values);
  if (band) {
    flat.push(...band.low, ...band.high);
  }
  const max = Math.max(1, ...flat);
  const lastDay = Math.max(1, days[days.length - 1] ?? 1);

  const x = (day: number) => pad.left + (day / lastDay) * innerW;
  const y = (value: number) => pad.top + (1 - value / max) * innerH;
  const path = (values: number[]) =>
    values
      .map((value, index) => `${index === 0 ? "M" : "L"} ${x(days[index] ?? index).toFixed(1)} ${y(value).toFixed(1)}`)
      .join(" ");

  let bandPath = "";
  if (band && band.high.length > 1) {
    const forward = band.high.map((value, index) => `${index === 0 ? "M" : "L"} ${x(days[index] ?? index).toFixed(1)} ${y(value).toFixed(1)}`);
    const back = [...band.low]
      .reverse()
      .map((value, index) => {
        const dayIndex = band.low.length - 1 - index;
        return `L ${x(days[dayIndex] ?? dayIndex).toFixed(1)} ${y(value).toFixed(1)}`;
      });
    bandPath = `${forward.join(" ")} ${back.join(" ")} Z`;
  }

  const ticks = 4;
  const grid = Array.from({ length: ticks + 1 }, (_, index) => {
    const value = (max * index) / ticks;
    return { value, y: y(value) };
  });

  return (
    <figure className="chart">
      <figcaption>{title}</figcaption>
      <svg viewBox={`0 0 ${width} ${height}`} role="img" aria-label={title}>
        {grid.map((tick) => (
          <g key={tick.value}>
            <line x1={pad.left} x2={width - pad.right} y1={tick.y} y2={tick.y} className="grid" />
            <text x={pad.left - 8} y={tick.y + 4} className="tick" textAnchor="end">
              {Math.round(tick.value)}
            </text>
          </g>
        ))}
        <text x={pad.left} y={height - 8} className="tick">
          día 0
        </text>
        <text x={width - pad.right} y={height - 8} className="tick" textAnchor="end">
          día {lastDay}
        </text>
        {bandPath ? <path d={bandPath} fill={band?.color} opacity={0.18} /> : null}
        {series.map((item) => (
          <path key={item.name} d={path(item.values)} fill="none" stroke={item.color} strokeWidth={2.4} />
        ))}
      </svg>
      <ul className="legend">
        {series.map((item) => (
          <li key={item.name}>
            <i style={{ background: item.color }} />
            {item.name}
          </li>
        ))}
      </ul>
    </figure>
  );
}
