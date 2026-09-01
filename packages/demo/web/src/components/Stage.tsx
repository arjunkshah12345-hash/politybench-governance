import { useEffect, useRef, useState } from "react";
import type { CountryReport } from "../types";

/** Soft looping pad — starts only after user gesture / toggle. */
export function useAmbientHum(on: boolean, muted: boolean) {
  const ref = useRef<{
    ctx: AudioContext;
    osc: OscillatorNode;
    osc2: OscillatorNode;
    gain: GainNode;
  } | null>(null);

  useEffect(() => {
    if (!on || muted) {
      if (ref.current) {
        try {
          ref.current.gain.gain.exponentialRampToValueAtTime(0.0001, ref.current.ctx.currentTime + 0.2);
          setTimeout(() => {
            try {
              ref.current?.osc.stop();
              ref.current?.osc2.stop();
              ref.current?.ctx.close();
            } catch {
              /* */
            }
            ref.current = null;
          }, 250);
        } catch {
          ref.current = null;
        }
      }
      return;
    }
    try {
      const Ctx = window.AudioContext || (window as unknown as { webkitAudioContext: typeof AudioContext }).webkitAudioContext;
      const ctx = new Ctx();
      const osc = ctx.createOscillator();
      const osc2 = ctx.createOscillator();
      const gain = ctx.createGain();
      const filter = ctx.createBiquadFilter();
      filter.type = "lowpass";
      filter.frequency.value = 420;
      osc.type = "sine";
      osc2.type = "triangle";
      osc.frequency.value = 110;
      osc2.frequency.value = 164.8;
      gain.gain.value = 0.0001;
      osc.connect(filter);
      osc2.connect(filter);
      filter.connect(gain);
      gain.connect(ctx.destination);
      osc.start();
      osc2.start();
      gain.gain.exponentialRampToValueAtTime(0.018, ctx.currentTime + 0.8);
      ref.current = { ctx, osc, osc2, gain };
    } catch {
      /* autoplay */
    }
    return () => {
      if (ref.current) {
        try {
          ref.current.osc.stop();
          ref.current.osc2.stop();
          ref.current.ctx.close();
        } catch {
          /* */
        }
        ref.current = null;
      }
    };
  }, [on, muted]);
}

export function MonthCalendar({
  trajectory,
  month,
  onChange,
  events = [],
  bookmarks = [],
}: {
  trajectory: Array<Record<string, number>>;
  month: number;
  onChange: (m: number) => void;
  events?: Array<{ month: number; type: string }>;
  bookmarks?: number[];
}) {
  if (!trajectory.length) return null;
  const eventSet = new Set(events.map((e) => Number(e.month)));
  const bm = new Set(bookmarks);
  return (
    <div className="month-calendar">
      <h4>📅 Term calendar</h4>
      <div className="cal-grid">
        {trajectory.map((_, i) => {
          const row = trajectory[i];
          const u = Number(row.unemployment ?? 0);
          const hot = u > 0.14 || Number(row.debt_gdp ?? 0) > 1.5;
          return (
            <button
              key={i}
              type="button"
              className={`cal-cell ${i === month ? "active" : ""} ${eventSet.has(i) ? "evt" : ""} ${hot ? "hot" : ""} ${bm.has(i) ? "bm" : ""}`}
              onClick={() => onChange(i)}
              title={`M${i} · U ${(u * 100).toFixed(0)}%`}
            >
              {i}
            </button>
          );
        })}
      </div>
    </div>
  );
}

export function RegionHeat({
  regions,
  unemployment,
  damage,
  trust,
}: {
  regions: CountryReport["regions"];
  unemployment: number;
  damage: number;
  trust: number;
}) {
  return (
    <div className="region-heat">
      <h4>🗺 Regions · live pressure</h4>
      <div className="rh-map">
        {regions.map((r, i) => {
          const pressure = Math.min(
            1,
            r.damage * 0.5 + damage * 0.25 + unemployment * 0.8 * (1 + i * 0.05) + (1 - trust) * 0.2 * r.population_share
          );
          const hue = 120 - pressure * 120;
          return (
            <div
              key={r.name}
              className="rh-cell"
              style={{
                flex: Math.max(0.15, r.population_share),
                background: `hsl(${hue} 55% ${42 - pressure * 12}%)`,
              }}
              title={`${r.name}: pressure ${(pressure * 100).toFixed(0)}`}
            >
              <strong>{r.name.slice(0, 8)}</strong>
              <span>{(pressure * 100).toFixed(0)}</span>
            </div>
          );
        })}
      </div>
    </div>
  );
}

export function Gauge({
  label,
  value,
  max = 1,
  warnAt,
  invertWarn = false,
  format,
}: {
  label: string;
  value: number;
  max?: number;
  warnAt?: number;
  invertWarn?: boolean;
  format: (v: number) => string;
}) {
  const pct = Math.max(0, Math.min(1, value / max));
  const angle = -90 + pct * 180;
  const warn =
    warnAt != null && (invertWarn ? value < warnAt : value > warnAt);
  return (
    <div className={`gauge ${warn ? "warn" : ""}`}>
      <svg viewBox="0 0 60 36" className="gauge-svg">
        <path d="M6 32 A24 24 0 0 1 54 32" fill="none" stroke="#3d2914" strokeWidth="4" />
        <path
          d="M6 32 A24 24 0 0 1 54 32"
          fill="none"
          stroke={warn ? "#c0392b" : "#e8a838"}
          strokeWidth="4"
          strokeDasharray={`${pct * 75} 75`}
        />
        <line
          x1="30"
          y1="32"
          x2="30"
          y2="12"
          stroke="#1a1008"
          strokeWidth="2"
          transform={`rotate(${angle} 30 32)`}
        />
      </svg>
      <span className="gauge-label">{label}</span>
      <strong>{format(value)}</strong>
    </div>
  );
}

export function ViewWipe({ token }: { token: string }) {
  const [show, setShow] = useState(false);
  const prev = useRef(token);
  useEffect(() => {
    if (prev.current === token) return;
    prev.current = token;
    setShow(true);
    const t = setTimeout(() => setShow(false), 420);
    return () => clearTimeout(t);
  }, [token]);
  if (!show) return null;
  return <div className="view-wipe" aria-hidden />;
}

const PREFS_KEY = "politybench.demo.prefs.v1";

export function loadPrefs(): {
  muted?: boolean;
  ambient?: boolean;
  speed?: number;
  bookmarks?: number[];
} {
  try {
    return JSON.parse(localStorage.getItem(PREFS_KEY) || "{}");
  } catch {
    return {};
  }
}

export function savePrefs(p: Record<string, unknown>) {
  try {
    const cur = loadPrefs();
    localStorage.setItem(PREFS_KEY, JSON.stringify({ ...cur, ...p }));
  } catch {
    /* */
  }
}

export function eventMonths(country?: CountryReport | null, extra?: CountryReport | null): number[] {
  const set = new Set<number>();
  for (const c of [country, extra]) {
    if (!c) continue;
    c.timeline.forEach((e) => set.add(Number(e.month)));
    (c.policy_log || []).forEach((p) => {
      if (p.month != null) set.add(Number(p.month));
    });
  }
  return [...set].sort((a, b) => a - b);
}

export function nextEventMonth(from: number, months: number[], dir: 1 | -1): number | null {
  if (dir > 0) {
    const hit = months.find((m) => m > from);
    return hit ?? null;
  }
  for (let i = months.length - 1; i >= 0; i--) {
    if (months[i] < from) return months[i];
  }
  return null;
}

export function PlayheadSparkline({
  trajectory,
  month,
  field = "gdp",
}: {
  trajectory: Array<Record<string, number>>;
  month: number;
  field?: string;
}) {
  if (trajectory.length < 2) return null;
  const vals = trajectory.map((r) => Number(r[field] ?? 0));
  const min = Math.min(...vals);
  const max = Math.max(...vals);
  const range = max - min || 1;
  const w = 120;
  const h = 28;
  const pts = vals
    .map((v, i) => {
      const x = (i / (vals.length - 1)) * w;
      const y = h - 2 - ((v - min) / range) * (h - 4);
      return `${x},${y}`;
    })
    .join(" ");
  const px = (month / Math.max(vals.length - 1, 1)) * w;
  return (
    <div className="playhead-spark">
      <svg viewBox={`0 0 ${w} ${h}`} width={w} height={h}>
        <polyline points={pts} fill="none" stroke="#58d68d" strokeWidth="2" />
        <line x1={px} y1={0} x2={px} y2={h} stroke="#e8a838" strokeWidth="2" />
        <circle cx={px} cy={h - 2 - ((vals[month] - min) / range) * (h - 4)} r="3" fill="#ffe566" stroke="#000" strokeWidth="1" />
      </svg>
      <span>{field.toUpperCase()}</span>
    </div>
  );
}

export function CrisisVignette({
  active,
  kind = "crisis",
}: {
  active: boolean;
  kind?: "crisis" | "boom";
}) {
  if (!active) return null;
  return <div className={`crisis-vignette kind-${kind}`} aria-hidden />;
}

export function NextCrisisChip({
  month,
  events,
  onJump,
}: {
  month: number;
  events: Array<{ month: number; type: string; label: string; severity: number }>;
  onJump: (m: number) => void;
}) {
  const next = events
    .filter((e) => Number(e.month) > month && (e.type === "disaster" || e.type === "fiscal" || e.type === "epidemic" || e.severity >= 0.5))
    .sort((a, b) => a.month - b.month)[0];
  if (!next) {
    return (
      <div className="next-crisis calm">
        <span>NO MAJOR CRISIS AHEAD</span>
      </div>
    );
  }
  const eta = Number(next.month) - month;
  return (
    <button type="button" className="next-crisis" onClick={() => onJump(Number(next.month))}>
      <span className="nc-eta">T−{eta}</span>
      <span>
        Next: {next.label.slice(0, 36)}
        {next.label.length > 36 ? "…" : ""}
      </span>
    </button>
  );
}

export function DualRadar({
  left,
  right,
}: {
  left: Record<string, number>;
  right: Record<string, number>;
}) {
  const keys = Array.from(new Set([...Object.keys(left), ...Object.keys(right)]));
  if (!keys.length) return null;
  const n = keys.length;
  const cx = 50;
  const cy = 50;
  const r = 36;
  const poly = (dims: Record<string, number>) =>
    keys
      .map((k, i) => {
        const angle = (Math.PI * 2 * i) / n - Math.PI / 2;
        const v = Math.max(0, Math.min(1, dims[k] ?? 0));
        return `${cx + Math.cos(angle) * r * v},${cy + Math.sin(angle) * r * v}`;
      })
      .join(" ");
  const ring = keys
    .map((_, i) => {
      const angle = (Math.PI * 2 * i) / n - Math.PI / 2;
      return `${cx + Math.cos(angle) * r},${cy + Math.sin(angle) * r}`;
    })
    .join(" ");
  return (
    <div className="dual-radar">
      <h4>Capability duel</h4>
      <svg viewBox="0 0 100 100">
        <polygon points={ring} className="radar-ring" />
        <polygon points={poly(left)} className="radar-fill left" />
        <polygon points={poly(right)} className="radar-fill right" />
        {keys.map((k, i) => {
          const angle = (Math.PI * 2 * i) / n - Math.PI / 2;
          return (
            <text
              key={k}
              x={cx + Math.cos(angle) * 46}
              y={cy + Math.sin(angle) * 46}
              className="radar-label"
              textAnchor="middle"
              dominantBaseline="middle"
            >
              {k.slice(0, 4)}
            </text>
          );
        })}
      </svg>
      <div className="dr-legend">
        <span className="l">Left</span>
        <span className="r">Right</span>
      </div>
    </div>
  );
}

export function copyBriefing(country: CountryReport) {
  const o = country.overview;
  const text = [
    `${country.country_name} (${country.model})`,
    `Rank #${country.rank} · Grade ${country.grade} · Robust ${country.evaluation.robust_score_single.toFixed(1)}`,
    `GDP ${o.gdp_index}% · U ${o.unemployment_pct.toFixed(1)}% · Trust ${(o.trust * 100).toFixed(0)} · Debt ${o.debt_gdp.toFixed(2)}×`,
    country.motto,
  ].join("\n");
  return navigator.clipboard?.writeText(text);
}
