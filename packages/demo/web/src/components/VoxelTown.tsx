/** Pixel voxel village that reacts to country health. */
export function VoxelTown({
  terrain,
  damage = 0,
  trust = 0.5,
  unemployment = 0.1,
  poverty = 0.15,
  debtGdp = 1,
}: {
  terrain: string;
  damage?: number;
  trust?: number;
  unemployment?: number;
  poverty?: number;
  debtGdp?: number;
}) {
  const ruined = damage > 0.15;
  const boom = trust > 0.7 && unemployment < 0.1 && poverty < 0.2;
  const crisis = debtGdp > 1.5 || unemployment > 0.15;

  return (
    <div className={`voxel-town-scene terrain-${terrain} ${ruined ? "ruined" : ""} ${boom ? "boom" : ""} ${crisis ? "crisis" : ""}`}>
      <div className="vt-sky">
        <span className="vt-sun" />
        <span className="vt-cloud c1" />
        <span className="vt-cloud c2" />
      </div>
      <div className="vt-ground">
        <div className={`vt-bldg capitol ${ruined ? "damaged" : ""}`}>
          <div className="vt-roof" />
          <div className="vt-wall">
            <i className="vt-win" />
            <i className="vt-door" />
            <i className="vt-win" />
          </div>
          <div className={`vt-flag ${trust > 0.6 ? "flying" : ""}`} />
        </div>
        <div className={`vt-bldg house ${poverty > 0.3 ? "poor" : ""}`}>
          <div className="vt-roof red" />
          <div className="vt-wall">
            <i className="vt-win" />
          </div>
        </div>
        <div className="vt-bldg shop">
          <div className="vt-roof blue" />
          <div className="vt-wall">
            <i className="vt-win" />
          </div>
        </div>
        <div className="vt-tree" />
        <div className="vt-tree short" />
        <div className="vt-people">
          {Array.from({ length: crisis ? 2 : boom ? 5 : 3 }).map((_, i) => (
            <span key={i} className={`vt-person p${i}`} style={{ animationDelay: `${i * 0.2}s` }}>
              {unemployment > 0.15 && i === 0 ? "😟" : boom ? "🙂" : "😐"}
            </span>
          ))}
        </div>
        {crisis && <div className="vt-banner">CRISIS</div>}
        {boom && <div className="vt-banner boom">BOOM</div>}
      </div>
    </div>
  );
}

export function DimRadar({ dims }: { dims: Record<string, number> }) {
  const keys = Object.keys(dims);
  if (!keys.length) return null;
  const n = keys.length;
  const cx = 50;
  const cy = 50;
  const r = 38;
  const pts = keys
    .map((k, i) => {
      const angle = (Math.PI * 2 * i) / n - Math.PI / 2;
      const v = Math.max(0, Math.min(1, dims[k] ?? 0));
      const x = cx + Math.cos(angle) * r * v;
      const y = cy + Math.sin(angle) * r * v;
      return `${x},${y}`;
    })
    .join(" ");
  const ring = keys
    .map((_, i) => {
      const angle = (Math.PI * 2 * i) / n - Math.PI / 2;
      return `${cx + Math.cos(angle) * r},${cy + Math.sin(angle) * r}`;
    })
    .join(" ");

  return (
    <div className="dim-radar">
      <svg viewBox="0 0 100 100">
        <polygon points={ring} className="radar-ring" />
        <polygon points={pts} className="radar-fill" />
        {keys.map((k, i) => {
          const angle = (Math.PI * 2 * i) / n - Math.PI / 2;
          const lx = cx + Math.cos(angle) * 46;
          const ly = cy + Math.sin(angle) * 46;
          return (
            <text key={k} x={lx} y={ly} className="radar-label" textAnchor="middle" dominantBaseline="middle">
              {k.slice(0, 4)}
            </text>
          );
        })}
      </svg>
    </div>
  );
}

export function MonthScrubber({
  trajectory,
  month,
  onChange,
}: {
  trajectory: Array<Record<string, number>>;
  month: number;
  onChange: (m: number) => void;
}) {
  if (!trajectory.length) return null;
  const max = trajectory.length - 1;
  const row = trajectory[Math.min(month, max)] || trajectory[0];
  return (
    <div className="month-scrubber">
      <div className="scrub-controls">
        <button type="button" onClick={() => onChange(Math.max(0, month - 1))} disabled={month <= 0}>
          ◀
        </button>
        <input
          type="range"
          min={0}
          max={max}
          value={month}
          onChange={(e) => onChange(Number(e.target.value))}
        />
        <button type="button" onClick={() => onChange(Math.min(max, month + 1))} disabled={month >= max}>
          ▶
        </button>
      </div>
      <div className="scrub-readout">
        <strong>
          Year {row.year} · Month {row.month}
        </strong>
        <span>GDP {(Number(row.gdp) || 0).toFixed(0)}</span>
        <span>U {(Number(row.unemployment || 0) * 100).toFixed(1)}%</span>
        <span>Trust {(Number(row.trust || 0) * 100).toFixed(0)}</span>
        <span>Debt {(Number(row.debt_gdp || 0)).toFixed(2)}×</span>
      </div>
    </div>
  );
}
