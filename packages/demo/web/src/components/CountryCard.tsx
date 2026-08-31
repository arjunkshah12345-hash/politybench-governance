import type { CountryReport } from "../types";
import { CitizenGrid, CitizenLegend } from "./CitizenGrid";

function MiniChart({ trajectory, field, color }: { trajectory: CountryReport["trajectory"]; field: string; color: string }) {
  const vals = trajectory.map((r) => Number(r[field] ?? 0));
  if (!vals.length) return null;
  const min = Math.min(...vals);
  const max = Math.max(...vals);
  const range = max - min || 1;
  const points = vals
    .map((v, i) => {
      const x = (i / Math.max(vals.length - 1, 1)) * 100;
      const y = 100 - ((v - min) / range) * 100;
      return `${x},${y}`;
    })
    .join(" ");
  return (
    <svg viewBox="0 0 100 100" preserveAspectRatio="none" className="mini-chart">
      <polyline points={points} fill="none" stroke={color} strokeWidth="3" vectorEffect="non-scaling-stroke" />
    </svg>
  );
}

export function CountryCard({
  country,
  selected,
  onSelect,
}: {
  country: CountryReport;
  selected: boolean;
  onSelect: () => void;
}) {
  const o = country.overview;
  const score = country.evaluation.robust_score_single;
  const [c1, c2, c3] = country.flag;

  return (
    <button
      type="button"
      className={`country-card ${selected ? "selected" : ""} terrain-${country.terrain}`}
      onClick={onSelect}
    >
      <div className="country-flag" style={{ background: `linear-gradient(180deg, ${c1} 33%, ${c2} 33%, ${c2} 66%, ${c3} 66%)` }} />
      <div className="country-card__head">
        <span className="country-leader">{country.sprite}</span>
        <div>
          <h3>{country.country_name}</h3>
          <p className="country-agent">{country.model}</p>
        </div>
        <div className="country-score">
          <strong>{score.toFixed(0)}</strong>
          <small>robust</small>
        </div>
      </div>

      <div className="country-voxel-map" aria-hidden>
        <div className="voxel-block house" />
        <div className="voxel-block tree" />
        <div className="voxel-block field" />
      </div>

      <CitizenGrid citizens={country.citizens.slice(0, 32)} />

      <div className="country-stats">
        <div><span>GDP</span><strong>{o.gdp_index}%</strong></div>
        <div><span>Jobs</span><strong>{(100 - o.unemployment_pct).toFixed(0)}%</strong></div>
        <div><span>Trust</span><strong>{(o.trust * 100).toFixed(0)}</strong></div>
        <div><span>Debt</span><strong>{o.debt_gdp.toFixed(1)}×</strong></div>
      </div>

      <div className="country-sparklines">
        <MiniChart trajectory={country.trajectory} field="gdp" color="#58d68d" />
        <MiniChart trajectory={country.trajectory} field="trust" color="#5dade2" />
        <MiniChart trajectory={country.trajectory} field="unemployment" color="#e74c3c" />
      </div>

      {country.integrity.llm_calls > 0 && (
        <p className="llm-badge">{country.integrity.llm_calls} LLM decisions</p>
      )}
    </button>
  );
}

export function CountryDetail({ country }: { country: CountryReport }) {
  const o = country.overview;
  const dims = country.evaluation.dims;

  return (
    <div className="country-detail">
      <header className="detail-header">
        <span className="detail-leader">{country.sprite}</span>
        <div>
          <h2>{country.country_name}</h2>
          <p>{country.leader_title} · {country.motto}</p>
          <p className="detail-meta">
            Agent <code>{country.agent_id}</code> · seed {country.seed} · {country.scenario.replace(/_/g, " ")}
          </p>
        </div>
      </header>

      <div className="detail-grid">
        <section className="detail-panel">
          <h4>Population</h4>
          <p className="big-num">{(o.population / 1_000_000).toFixed(1)}M</p>
          <CitizenGrid citizens={country.citizens} />
          <CitizenLegend />
        </section>

        <section className="detail-panel">
          <h4>Regional overview</h4>
          <table className="pixel-table">
            <thead>
              <tr>
                <th>Region</th>
                <th>Pop</th>
                <th>GDP</th>
                <th>Damage</th>
              </tr>
            </thead>
            <tbody>
              {country.regions.map((r) => (
                <tr key={r.name}>
                  <td>{r.name}</td>
                  <td>{(r.population_share * 100).toFixed(0)}%</td>
                  <td>{(r.gdp_share * 100).toFixed(0)}%</td>
                  <td>{(r.damage * 100).toFixed(0)}%</td>
                </tr>
              ))}
            </tbody>
          </table>
        </section>

        <section className="detail-panel">
          <h4>Seven dimensions</h4>
          {Object.entries(dims).map(([k, v]) => (
            <div className="stat-row" key={k}>
              <span>{k}</span>
              <div className="stat-bar-track">
                <span className="stat-bar-fill" style={{ width: `${v * 100}%` }} />
              </div>
              <span>{v.toFixed(2)}</span>
            </div>
          ))}
        </section>

        <section className="detail-panel">
          <h4>Timeline</h4>
          <ul className="timeline">
            {country.timeline.map((e, i) => (
              <li key={i} className={`evt-${e.type}`}>
                <span className="evt-month">M{e.month}</span>
                <span>{e.label}</span>
              </li>
            ))}
          </ul>
        </section>

        <section className="detail-panel span-2">
          <h4>Macro trajectory</h4>
          <div className="trajectory-charts">
            {(["gdp", "unemployment", "trust", "debt_gdp"] as const).map((f) => (
              <div key={f} className="traj-block">
                <label>{f}</label>
                <MiniChart trajectory={country.trajectory} field={f} color="#1f6f5b" />
              </div>
            ))}
          </div>
        </section>

        <section className="detail-panel">
          <h4>Integrity</h4>
          <ul className="integrity-list">
            <li>Hard violations: {country.integrity.hard_violations}</li>
            <li>Rejected actions: {country.integrity.rejected_actions}</li>
            <li>LLM policy calls: {country.integrity.llm_calls}</li>
            <li>Utility: {country.evaluation.utility.toFixed(3)}</li>
            <li>Robust score: {country.evaluation.robust_score_single.toFixed(1)}</li>
          </ul>
        </section>
      </div>
    </div>
  );
}
