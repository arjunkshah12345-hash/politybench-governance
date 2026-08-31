import { useEffect, useMemo, useState } from "react";
import type { CountryReport } from "../types";
import { CitizenGrid, CitizenLegend, MoodBar } from "./CitizenGrid";
import { DimRadar, MonthScrubber, VoxelTown } from "./VoxelTown";
import { narrativeFor } from "./Narrative";

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

const RANK_BADGE = ["🥇", "🥈", "🥉"];

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
      <span className="rank-badge">{RANK_BADGE[country.rank - 1] || `#${country.rank}`}</span>
      <span className={`grade-pill grade-${country.grade}`}>{country.grade}</span>
      <div
        className="country-flag"
        style={{ background: `linear-gradient(180deg, ${c1} 33%, ${c2} 33%, ${c2} 66%, ${c3} 66%)` }}
      />
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

      <VoxelTown
        terrain={country.terrain}
        damage={o.damage}
        trust={o.trust}
        unemployment={o.unemployment_pct / 100}
        poverty={o.poverty_pct / 100}
        debtGdp={o.debt_gdp}
      />

      <MoodBar summary={country.mood_summary || {}} />
      <CitizenGrid citizens={country.citizens} size={40} />

      <div className="country-stats">
        <div>
          <span>GDP</span>
          <strong>{o.gdp_index}%</strong>
        </div>
        <div>
          <span>Jobs</span>
          <strong>{(100 - o.unemployment_pct).toFixed(0)}%</strong>
        </div>
        <div>
          <span>Trust</span>
          <strong>{(o.trust * 100).toFixed(0)}</strong>
        </div>
        <div>
          <span>Debt</span>
          <strong>{o.debt_gdp.toFixed(1)}×</strong>
        </div>
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

export function CountryDetail({
  country,
  month: controlledMonth,
  onMonthChange,
}: {
  country: CountryReport;
  month?: number;
  onMonthChange?: (m: number) => void;
}) {
  const o = country.overview;
  const dims = country.evaluation.dims;
  const [localMonth, setLocalMonth] = useState(() => Math.max(0, country.trajectory.length - 1));
  const month = controlledMonth ?? localMonth;
  const setMonth = onMonthChange ?? setLocalMonth;

  useEffect(() => {
    if (controlledMonth == null) {
      setLocalMonth(Math.max(0, country.trajectory.length - 1));
    }
  }, [country.agent_id, country.trajectory.length, controlledMonth]);

  const snap = useMemo(() => {
    const t = country.trajectory[Math.min(month, Math.max(0, country.trajectory.length - 1))];
    return t || {};
  }, [country.trajectory, month]);

  const liveUnemp = Number(snap.unemployment ?? o.unemployment_pct / 100);
  const liveTrust = Number(snap.trust ?? o.trust);
  const liveDebt = Number(snap.debt_gdp ?? o.debt_gdp);
  const liveDamage = Number(snap.damage ?? o.damage);
  const livePoverty = Number(snap.poverty ?? o.poverty_pct / 100);

  return (
    <div className="country-detail">
      <header className="detail-header">
        <span className="detail-leader">{country.sprite}</span>
        <div>
          <h2>
            {country.country_name}{" "}
            <span className={`grade-pill grade-${country.grade}`}>{country.grade}</span>
            <span className="rank-inline">Rank #{country.rank}</span>
          </h2>
          <p>
            {country.leader_title} · {country.motto}
          </p>
          <p className="detail-meta">
            Agent <code>{country.agent_id}</code> · seed {country.seed} ·{" "}
            {country.scenario.replace(/_/g, " ")}
          </p>
        </div>
      </header>

      <p className="narrative-box">{narrativeFor(country)}</p>

      <VoxelTown
        terrain={country.terrain}
        damage={liveDamage}
        trust={liveTrust}
        unemployment={liveUnemp}
        poverty={livePoverty}
        debtGdp={liveDebt}
      />

      <MonthScrubber trajectory={country.trajectory} month={month} onChange={setMonth} />

      <div className="detail-grid">
        <section className="detail-panel">
          <h4>Population mood</h4>
          <p className="big-num">{(o.population / 1_000_000).toFixed(1)}M citizens</p>
          <MoodBar summary={country.mood_summary || {}} />
          <CitizenGrid citizens={country.citizens} />
          <CitizenLegend />
        </section>

        <section className="detail-panel">
          <h4>Capability radar</h4>
          <DimRadar dims={dims} />
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
                <th>Services</th>
              </tr>
            </thead>
            <tbody>
              {country.regions.map((r) => (
                <tr key={r.name}>
                  <td>{r.name}</td>
                  <td>{(r.population_share * 100).toFixed(0)}%</td>
                  <td>{(r.gdp_share * 100).toFixed(0)}%</td>
                  <td>{(r.damage * 100).toFixed(0)}%</td>
                  <td>{(r.services * 100).toFixed(0)}%</td>
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
          <h4>Policy log</h4>
          {country.policy_log?.length ? (
            <ul className="policy-log">
              {country.policy_log.map((p, i) => (
                <li key={i}>
                  <span className="evt-month">M{p.month ?? i}</span>
                  <span className={`src-${p.source}`}>{p.source}</span>
                  <span>{p.label}</span>
                  {p.debt_gdp != null && (
                    <small> debt {(Number(p.debt_gdp) * 100).toFixed(0)}% GDP</small>
                  )}
                </li>
              ))}
            </ul>
          ) : (
            <p className="muted">Monthly policy bundles recorded from simulation.</p>
          )}
        </section>

        <section className="detail-panel">
          <h4>Crisis timeline</h4>
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
