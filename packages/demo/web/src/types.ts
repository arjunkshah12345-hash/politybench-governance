export type Citizen = { mood: string; employed: boolean; cohort: number; region?: string };

export type CountryReport = {
  agent_id: string;
  model: string;
  seed: number;
  scenario: string;
  rank: number;
  grade: string;
  country_name: string;
  motto: string;
  leader_title: string;
  sprite: string;
  flag: string[];
  terrain: string;
  overview: {
    population: number;
    gdp_index: number;
    unemployment_pct: number;
    debt_gdp: number;
    trust: number;
    poverty_pct: number;
    infected: number;
    deaths: number;
    damage: number;
    inflation_pct: number;
    admin_capacity?: number;
    corruption?: number;
  };
  evaluation: {
    utility: number;
    robust_score_single: number;
    dims: Record<string, number>;
  };
  citizens: Citizen[];
  mood_summary?: Record<string, number>;
  regions: Array<{
    name: string;
    population_share: number;
    gdp_share: number;
    damage: number;
    services: number;
  }>;
  timeline: Array<{
    month: number;
    year?: number;
    type: string;
    label: string;
    severity: number;
  }>;
  policy_log?: Array<{
    month?: number;
    source: string;
    label: string;
    debt_gdp?: number;
    unemployment?: number;
  }>;
  trajectory: Array<Record<string, number>>;
  integrity: {
    hard_violations: number;
    rejected_actions: number;
    llm_calls: number;
  };
};

export type BenchLive = {
  generated_at: string;
  bench_kind: string;
  scenario: string;
  fidelity: string;
  seeds: number;
  llm_interval_months: number;
  countries: CountryReport[];
  summary: {
    robust_scores: Record<string, number>;
    mean_utility: Record<string, number>;
    pareto_frontier: string[];
    best_baseline?: { agent: string; robust_score: number };
    head_to_head?: Array<{
      model: string;
      vs_baseline: string;
      score_delta: number;
      won: boolean;
    }>;
  };
};
