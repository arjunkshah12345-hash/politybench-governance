import { useEffect, useMemo, useState } from "react";
import { useDialKit } from "dialkit";
import { motion } from "motion/react";

type Results = {
  scenario: string;
  seeds: number;
  robust_scores: Record<string, number>;
  mean_utility: Record<string, number>;
  mean_dims: Record<string, Record<string, number>>;
  pareto_frontier: string[];
  weight_sensitivity: Record<string, { mean_rank: number; p_top1: number; rank_interval: number[] }>;
  weight_heatmap?: Array<{
    focus_dim: string;
    rankings: Record<string, number>;
    winner: string;
  }>;
};

type Calibration = {
  greece?: { rmse_gdp_index_calibration: number; rmse_gdp_index_validation: number };
  japan_geje?: { rmse_reconstruction_calibration: number; rmse_reconstruction_holdout: number };
  pandemic?: { rmse_trust_calibration: number; rmse_trust_validation: number };
};

const DIMS = [
  { id: "economic", icon: "💰", color: "#f4d03f" },
  { id: "human", icon: "❤️", color: "#e74c3c" },
  { id: "stability", icon: "🛡️", color: "#5dade2" },
  { id: "equity", icon: "⚖️", color: "#bb8fce" },
  { id: "resilience", icon: "🌱", color: "#58d68d" },
  { id: "legitimacy", icon: "📜", color: "#f5b041" },
  { id: "environment", icon: "🌍", color: "#48c9b0" },
] as const;

const FALLBACK: Results = {
  scenario: "macro_fiscal_crisis",
  seeds: 8,
  robust_scores: { hold_policy: 61.2, rule_based: 68.4, random_valid: 58.1, simple_mpc: 69.0 },
  mean_utility: { hold_policy: 0.62, rule_based: 0.70, random_valid: 0.59, simple_mpc: 0.71 },
  mean_dims: {
    rule_based: {
      economic: 0.56,
      human: 0.81,
      stability: 0.79,
      equity: 0.35,
      resilience: 0.91,
      legitimacy: 0.99,
      environment: 0.63,
    },
    hold_policy: {
      economic: 0.48,
      human: 0.78,
      stability: 0.72,
      equity: 0.30,
      resilience: 0.85,
      legitimacy: 0.96,
      environment: 0.58,
    },
  },
  pareto_frontier: ["rule_based", "simple_mpc"],
  weight_sensitivity: {
    rule_based: { mean_rank: 1.4, p_top1: 0.55, rank_interval: [1, 3] },
    simple_mpc: { mean_rank: 1.6, p_top1: 0.40, rank_interval: [1, 3] },
  },
};

const AGENT_SPRITES: Record<string, string> = {
  hold_policy: "🧑‍🌾",
  rule_based: "👨‍⚖️",
  random_valid: "🎲",
  simple_mpc: "🧮",
};

function PixelPanel({
  title,
  children,
  className = "",
  accent,
}: {
  title: string;
  children: React.ReactNode;
  className?: string;
  accent?: string;
}) {
  return (
    <div className={`pixel-panel ${className}`} style={{ "--panel-accent": accent } as React.CSSProperties}>
      <div className="pixel-panel__tab">
        <span className="pixel-panel__bolt" />
        <h2>{title}</h2>
        <span className="pixel-panel__bolt" />
      </div>
      <div className="pixel-panel__body">{children}</div>
    </div>
  );
}

function StatBar({ label, value, color, icon }: { label: string; value: number; color: string; icon: string }) {
  const pct = Math.round(value * 100);
  return (
    <div className="stat-row">
      <span className="stat-label">
        {icon} {label}
      </span>
      <div className="stat-bar-track">
        <motion.div
          className="stat-bar-fill"
          style={{ backgroundColor: color }}
          initial={{ width: 0 }}
          animate={{ width: `${pct}%` }}
          transition={{ type: "spring", stiffness: 120, damping: 18 }}
        />
        <span className="stat-bar-shine" />
      </div>
      <span className="stat-val">{pct}</span>
    </div>
  );
}

function VoxelScene({ sunY }: { sunY: number }) {
  return (
    <div className="voxel-scene" aria-hidden>
      <motion.div
        className="voxel-sun"
        animate={{ y: [0, -6, 0] }}
        transition={{ duration: 4, repeat: Infinity, ease: "easeInOut" }}
        style={{ top: `${sunY}%` }}
      />
      <div className="voxel-cloud c1" />
      <div className="voxel-cloud c2" />
      <div className="voxel-cloud c3" />
      <div className="voxel-ground">
        <div className="voxel-hills" />
        <div className="voxel-town">
          <div className="voxel-building capitol">
            <div className="voxel-roof" />
            <div className="voxel-wall">
              <span className="voxel-window" />
              <span className="voxel-door" />
              <span className="voxel-window" />
            </div>
            <div className="voxel-flag" />
          </div>
          <div className="voxel-building farm">
            <div className="voxel-roof red" />
            <div className="voxel-wall">
              <span className="voxel-window" />
            </div>
          </div>
          <div className="voxel-tree t1" />
          <div className="voxel-tree t2" />
          <div className="voxel-tree t3" />
          <div className="voxel-fence" />
        </div>
      </div>
    </div>
  );
}

export default function App() {
  const theme = useDialKit("Pixel Theme", {
    skyTop: "#5eb8ff",
    skyBottom: "#b8e4ff",
    grass: "#5a9e2f",
    dirt: "#8b6914",
    wood: "#6b4423",
    panelBg: "#f5e6c8",
    panelEdge: "#3d2914",
    accent: "#e8a838",
    scanlines: [0.06, 0, 0.25],
    pixelGlow: [0.35, 0, 1],
    sunHeight: [18, 8, 35],
    floatAmount: [6, 0, 16],
  });

  const [data, setData] = useState<Results>(FALLBACK);
  const [calibration, setCalibration] = useState<Calibration | null>(null);
  const [agent, setAgent] = useState("rule_based");
  const [tick, setTick] = useState(0);

  useEffect(() => {
    fetch("/latest_results.json")
      .then((r) => (r.ok ? r.json() : Promise.reject()))
      .then((j) => {
        setData(j);
        const first = Object.keys(j.mean_dims || {})[0];
        if (first) setAgent(first);
      })
      .catch(() => undefined);
    fetch("/calibration_summary.json")
      .then((r) => (r.ok ? r.json() : Promise.reject()))
      .then(setCalibration)
      .catch(() => undefined);
  }, []);

  useEffect(() => {
    const id = setInterval(() => setTick((t) => t + 1), 1200);
    return () => clearInterval(id);
  }, []);

  const dims = data.mean_dims[agent] || data.mean_dims.rule_based || FALLBACK.mean_dims.rule_based;
  const agents = Object.keys(data.robust_scores);
  const maxScore = Math.max(...Object.values(data.robust_scores), 1);
  const heatmapRows = data.weight_heatmap || [];

  const leaderboard = useMemo(
    () =>
      Object.entries(data.robust_scores)
        .map(([name, score]) => ({ name, score, utility: data.mean_utility[name] || 0 }))
        .sort((a, b) => b.score - a.score),
    [data]
  );

  const cssVars = {
    "--sky-top": theme.skyTop,
    "--sky-bottom": theme.skyBottom,
    "--grass": theme.grass,
    "--dirt": theme.dirt,
    "--wood": theme.wood,
    "--panel-bg": theme.panelBg,
    "--panel-edge": theme.panelEdge,
    "--accent": theme.accent,
    "--scanline-opacity": theme.scanlines,
    "--pixel-glow": theme.pixelGlow,
    "--float-amt": `${theme.floatAmount}px`,
  } as React.CSSProperties;

  return (
    <div className="pixel-world" style={cssVars}>
      <div className="crt-overlay" style={{ opacity: theme.scanlines }} />
      <div className="pixel-stars" />

      <header className="pixel-header">
        <VoxelScene sunY={theme.sunHeight} />
        <div className="pixel-header__ui">
          <div className="sample-badge">◆ SAMPLE DEMO · NOT DEPLOYED ◆</div>
          <motion.h1
            className="pixel-title"
            animate={{ y: [0, -theme.floatAmount / 2, 0] }}
            transition={{ duration: 3, repeat: Infinity, ease: "easeInOut" }}
          >
            POLITY<span className="gold">BENCH</span>
          </motion.h1>
          <p className="pixel-subtitle">~ governance sim · year 2000 mode ~</p>
          <div className="pixel-disclaimer">
            ⚠ high score ≠ fit to govern a real country ⚠
          </div>
        </div>
      </header>

      <div className="pixel-hud">
        <div className="hud-coin">
          <span className="hud-icon">🏛️</span>
          <div>
            <small>SCENARIO</small>
            <strong>{data.scenario.replace(/_/g, " ")}</strong>
          </div>
        </div>
        <div className="hud-coin">
          <span className="hud-icon">🌾</span>
          <div>
            <small>SEEDS</small>
            <strong>{data.seeds}</strong>
          </div>
        </div>
        <div className="hud-coin">
          <span className="hud-icon">⏱️</span>
          <div>
            <small>TICK</small>
            <strong>{tick}</strong>
          </div>
        </div>
      </div>

      <main className="pixel-grid">
        <PixelPanel title="★ SCORE ★" className="span-score" accent={theme.accent}>
          <div className="agent-picker">
            {agents.map((a) => (
              <button
                key={a}
                type="button"
                className={`pixel-btn ${agent === a ? "active" : ""}`}
                onClick={() => setAgent(a)}
              >
                <span className="sprite">{AGENT_SPRITES[a] || "🤖"}</span>
                {a.replace(/_/g, " ")}
              </button>
            ))}
          </div>
          <div className="score-display">
            <motion.div
              key={agent}
              className="score-big"
              initial={{ scale: 0.8, opacity: 0 }}
              animate={{ scale: 1, opacity: 1 }}
              transition={{ type: "spring", bounce: 0.4 }}
            >
              {(data.robust_scores[agent] ?? 0).toFixed(1)}
            </motion.div>
            <div className="score-max">/ 100 robust</div>
            <div className="score-formula">0.75·E[G] + 0.25·CVaR₁₀%</div>
          </div>
        </PixelPanel>

        <PixelPanel title="♥ STATS ♥" className="span-stats">
          {DIMS.map((d) => (
            <StatBar
              key={d.id}
              label={d.id}
              value={dims[d.id] || 0}
              color={d.color}
              icon={d.icon}
            />
          ))}
        </PixelPanel>

        <PixelPanel title="⚔ LEADERBOARD ⚔" className="span-board">
          <div className="leaderboard">
            {leaderboard.map((row, i) => (
              <div key={row.name} className={`lb-row rank-${i + 1}`}>
                <span className="lb-rank">#{i + 1}</span>
                <span className="lb-sprite">{AGENT_SPRITES[row.name] || "🤖"}</span>
                <span className="lb-name">{row.name.replace(/_/g, " ")}</span>
                <div className="lb-bar-wrap">
                  <div
                    className="lb-bar"
                    style={{ width: `${(row.score / maxScore) * 100}%` }}
                  />
                </div>
                <span className="lb-score">{row.score.toFixed(1)}</span>
              </div>
            ))}
          </div>
          <p className="pixel-note">
            Pareto front: {(data.pareto_frontier || []).join(" · ") || "—"}
          </p>
        </PixelPanel>

        <PixelPanel title="📊 SENSITIVITY 📊" className="span-sense">
          <table className="pixel-table">
            <thead>
              <tr>
                <th>Agent</th>
                <th>Rank</th>
                <th>Top</th>
              </tr>
            </thead>
            <tbody>
              {Object.entries(data.weight_sensitivity || {}).map(([a, s]) => (
                <tr key={a}>
                  <td>
                    {AGENT_SPRITES[a]} {a.replace(/_/g, " ")}
                  </td>
                  <td>{s.mean_rank.toFixed(1)}</td>
                  <td>{(s.p_top1 * 100).toFixed(0)}%</td>
                </tr>
              ))}
            </tbody>
          </table>
        </PixelPanel>

        {calibration && (
          <PixelPanel title="🔬 CALIBRATION 🔬" className="span-cal">
            <div className="cal-grid">
              {calibration.greece && (
                <div className="cal-card">
                  <span>🇬🇷 GREECE</span>
                  <strong>
                    {calibration.greece.rmse_gdp_index_calibration.toFixed(1)} /{" "}
                    {calibration.greece.rmse_gdp_index_validation.toFixed(1)}
                  </strong>
                  <small>GDP RMSE cal/hold</small>
                </div>
              )}
              {calibration.japan_geje && (
                <div className="cal-card">
                  <span>🇯🇵 JAPAN GEJE</span>
                  <strong>
                    {calibration.japan_geje.rmse_reconstruction_calibration.toFixed(2)} /{" "}
                    {calibration.japan_geje.rmse_reconstruction_holdout.toFixed(2)}
                  </strong>
                  <small>Recon RMSE</small>
                </div>
              )}
              {calibration.pandemic && (
                <div className="cal-card">
                  <span>🦠 PANDEMIC</span>
                  <strong>
                    {calibration.pandemic.rmse_trust_calibration.toFixed(2)} /{" "}
                    {calibration.pandemic.rmse_trust_validation.toFixed(2)}
                  </strong>
                  <small>Trust RMSE</small>
                </div>
              )}
            </div>
            <p className="pixel-note">Validation only — never leaderboard worlds</p>
          </PixelPanel>
        )}

        {heatmapRows.length > 0 && (
          <PixelPanel title="🎨 WEIGHT MAP 🎨" className="span-heat">
            <div className="heat-grid">
              <div className="heat-row head">
                <span />
                {agents.map((a) => (
                  <span key={a}>{AGENT_SPRITES[a]}</span>
                ))}
              </div>
              {heatmapRows.map((row) => (
                <div className="heat-row" key={row.focus_dim}>
                  <span className="heat-dim">{row.focus_dim.slice(0, 5)}</span>
                  {agents.map((a) => {
                    const rank = row.rankings[a] || agents.length;
                    return (
                      <span
                        key={a}
                        className={`heat-cell r${rank}`}
                        title={`rank ${rank}`}
                      >
                        {rank}
                      </span>
                    );
                  })}
                </div>
              ))}
            </div>
          </PixelPanel>
        )}

        <PixelPanel title="📖 QUEST LOG 📖" className="span-log">
          <p className="quest-text">
            You are a constitutionally constrained national executive in a hybrid simulator.
            Partial observations. Delayed policies. Shocks from the east. Sample data from{" "}
            <code>latest_results.json</code>. Open the DialKit panel (bottom-right) to tune
            colors, scanlines, and float — dial in your perfect harvest-moon aesthetic.
          </p>
        </PixelPanel>
      </main>

      <footer className="pixel-footer">
        <span>PolityBench v0.1 · research sim</span>
        <span className="blink">▮</span>
        <span>press F12 for devtools</span>
      </footer>
    </div>
  );
}
