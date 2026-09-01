/** Pixel voxel village that reacts to country health. */
export function VoxelTown({
  terrain,
  damage = 0,
  trust = 0.5,
  unemployment = 0.1,
  poverty = 0.15,
  debtGdp = 1,
  calendarMonth = 6,
  dayPhase = "day",
  weather = "clear",
}: {
  terrain: string;
  damage?: number;
  trust?: number;
  unemployment?: number;
  poverty?: number;
  debtGdp?: number;
  calendarMonth?: number;
  dayPhase?: "dawn" | "day" | "dusk" | "night";
  weather?: "clear" | "rain" | "storm" | "snow";
}) {
  const ruined = damage > 0.15;
  const boom = trust > 0.7 && unemployment < 0.1 && poverty < 0.2;
  const crisis = debtGdp > 1.5 || unemployment > 0.15;
  const season =
    calendarMonth <= 2 || calendarMonth === 12
      ? "winter"
      : calendarMonth <= 5
        ? "spring"
        : calendarMonth <= 8
          ? "summer"
          : "autumn";

  const people = crisis || weather === "storm" ? 2 : boom ? 6 : dayPhase === "night" ? 1 : 4;
  const showRain = weather === "rain" || weather === "storm" || crisis;
  const showSnow = weather === "snow";

  return (
    <div
      className={`voxel-town-scene terrain-${terrain} season-${season} phase-${dayPhase} weather-${weather} ${ruined ? "ruined" : ""} ${boom ? "boom" : ""} ${crisis ? "crisis" : ""}`}
    >
      <div className="vt-sky">
        <span className={`vt-sun ${dayPhase === "night" ? "moon" : ""}`} />
        {dayPhase !== "night" && weather !== "storm" && (
          <>
            <span className="vt-cloud c1" />
            <span className="vt-cloud c2" />
          </>
        )}
        {dayPhase === "night" && (
          <div className="vt-stars" aria-hidden>
            {Array.from({ length: 6 }).map((_, i) => (
              <i key={i} style={{ left: `${12 + i * 14}%`, top: `${8 + (i % 3) * 10}%` }} />
            ))}
          </div>
        )}
        {showRain && (
          <div className={`vt-rain ${weather === "storm" ? "storm" : ""}`} aria-hidden>
            {Array.from({ length: weather === "storm" ? 14 : 8 }).map((_, i) => (
              <i key={i} style={{ left: `${6 + i * 7}%`, animationDelay: `${i * 0.09}s` }} />
            ))}
          </div>
        )}
        {showSnow && (
          <div className="vt-snow" aria-hidden>
            {Array.from({ length: 10 }).map((_, i) => (
              <i key={i} style={{ left: `${8 + i * 9}%`, animationDelay: `${i * 0.2}s` }} />
            ))}
          </div>
        )}
      </div>
      <div className="vt-ground">
        <div className={`vt-bldg capitol ${ruined ? "damaged" : ""}`}>
          <div className="vt-roof" />
          <div className="vt-wall">
            <i className={`vt-win ${dayPhase === "night" || dayPhase === "dusk" ? "lit" : ""}`} />
            <i className="vt-door" />
            <i className={`vt-win ${dayPhase === "night" ? "lit" : ""}`} />
          </div>
          <div className={`vt-flag ${trust > 0.6 ? "flying" : ""}`} />
          {!crisis && dayPhase !== "night" && <span className="vt-smoke" />}
        </div>
        <div className={`vt-bldg house ${poverty > 0.3 ? "poor" : ""}`}>
          <div className="vt-roof red" />
          <div className="vt-wall">
            <i className={`vt-win ${dayPhase === "night" ? "lit" : ""}`} />
          </div>
        </div>
        <div className={`vt-bldg shop ${boom ? "busy" : ""}`}>
          <div className="vt-roof blue" />
          <div className="vt-wall">
            <i className={`vt-win ${dayPhase !== "day" ? "lit" : ""}`} />
          </div>
          {boom && <span className="vt-coins">$</span>}
        </div>
        <div className="vt-tree" />
        <div className="vt-tree short" />
        <div className="vt-people">
          {Array.from({ length: people }).map((_, i) => (
            <span
              key={i}
              className={`vt-person walk p${i % 4}`}
              style={{ animationDelay: `${i * 0.35}s`, animationDuration: `${2.4 + (i % 3) * 0.4}s` }}
            >
              {unemployment > 0.15 && i === 0 ? "😟" : boom ? "🙂" : ruined ? "😮" : "😐"}
            </span>
          ))}
        </div>
        {crisis && <div className="vt-banner">CRISIS</div>}
        {boom && <div className="vt-banner boom">BOOM</div>}
        {weather === "storm" && <div className="vt-banner storm">STORM</div>}
        <span className="vt-clock">{dayPhase.toUpperCase()}</span>
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
  events = [],
}: {
  trajectory: Array<Record<string, number>>;
  month: number;
  onChange: (m: number) => void;
  events?: Array<{ month: number; type: string; label: string }>;
}) {
  if (!trajectory.length) return null;
  const max = trajectory.length - 1;
  const row = trajectory[Math.min(month, max)] || trajectory[0];
  const marks = events.filter((e) => e.month >= 0 && e.month <= max);

  return (
    <div className="month-scrubber">
      <div className="scrub-controls">
        <button type="button" onClick={() => onChange(Math.max(0, month - 1))} disabled={month <= 0}>
          ◀
        </button>
        <div className="scrub-track-wrap">
          <input
            type="range"
            min={0}
            max={max}
            value={month}
            onChange={(e) => onChange(Number(e.target.value))}
          />
          <div className="scrub-marks">
            {marks.map((e, i) => (
              <button
                key={`${e.month}-${e.type}-${i}`}
                type="button"
                className={`scrub-mark evt-${e.type}`}
                style={{ left: `${(e.month / Math.max(max, 1)) * 100}%` }}
                title={`M${e.month}: ${e.label}`}
                onClick={() => onChange(e.month)}
              />
            ))}
          </div>
        </div>
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
