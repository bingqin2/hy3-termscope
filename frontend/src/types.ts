export type ConfigId = "hy3-terminus-2" | "hy3-mini-swe-agent";
export type Outcome = "resolved" | "unresolved" | "inconclusive";
export type Process = "valid" | "partial" | "invalid";
export type Provenance = "official" | "evaluator" | "human" | "second_rater" | "mixed";
export type Difficulty = "easy" | "medium" | "hard";
export type Severity = "critical" | "high" | "medium";

export interface LeaderboardRow {
  config_id: ConfigId;
  label: string;
  n_runs: number;
  n_inconclusive: number;
  resolve_rate: number | null;
  process_validity_rate_predicted: number | null;
  process_validity_rate_adjudicated: number | null;
  tasks_won: number;
  provenance: Record<string, string>;
}

export interface LeaderboardData {
  sample: boolean;
  updated: string;
  rows: LeaderboardRow[];
}

export interface TaskCell {
  outcome: Outcome;
  reward: number | null;
  process: Process | null;
  process_provenance: Provenance;
  resolved_but_invalid: boolean | null;
}

export interface TaskRow {
  task_id: string;
  name: string;
  category: string;
  difficulty: Difficulty;
  cells: Record<ConfigId, TaskCell | null>;
}

export interface TasksData {
  sample: boolean;
  rows: TaskRow[];
}

export interface FailurePattern {
  error_type: string;
  label: string;
  severity: Severity;
  count: number;
  by_config: Record<ConfigId, number>;
}

export interface FailurePatternsData {
  sample: boolean;
  provenance: string;
  rows: FailurePattern[];
}

export interface RunStep {
  step_id: number;
  source: string;
  content: string;
  command: string | null;
  observation: string;
}

export interface FirstErrorLabel {
  location: "located" | "none" | "unlocatable";
  step_id: number | null;
}

export interface ReferenceReview {
  reviewer: string;
  provenance: Provenance;
  version: number;
  blinded: boolean;
  label: {
    process: Process | null;
    first_error: FirstErrorLabel | null;
    error_type: string | null;
  };
  notes: string;
}

export interface Run {
  run_id: string;
  task_id: string;
  config_id: ConfigId;
  difficulty: Difficulty;
  category: string;
  outcome: Outcome;
  reward: number | null;
  process: Process | null;
  process_provenance: Provenance;
  first_error_step: number | null;
  first_error_location: string | null;
  judge_earlier_step: number | null;
  error_types: string[];
  finding: string | null;
  replay: { localization: string; step: number | null } | null;
  judge_status: "ok" | "unavailable" | "context_limit" | null;
  checks: { name: string; status: string }[];
  steps: RunStep[];
  token_usage: { input: number | null; output: number | null; total: number | null } | null;
  wall_sec: number | null;
  reference_review: ReferenceReview | null;
}

export interface RunsData {
  sample: boolean;
  updated: string;
  runs: Run[];
}

export interface Ratio {
  num: number | null;
  den: number | null;
}

export interface ValidationData {
  sample: boolean;
  localization_exact: Ratio;
  localization_pm1: Ratio;
  localization_located_only: Ratio;
  reference_labels: Record<string, number> | null;
  false_positive_rate: Ratio;
  metric_definitions: Record<string, string>;
  consistency: {
    verdict_agreement: string;
    first_error_step_agreement: string;
    n_runs: number;
    flagged_run_stability: { run_id: string; verdict: string; step: string } | null;
  };
  fixture_gate_v1: string;
  regression: {
    fixture_gate_v2: { passed: boolean; valid: boolean; invalid: boolean } | null;
    metrics: {
      denominators: Record<string, number>;
      detection_nonvalid: Record<"v1" | "v2", string>;
      verdict_agreement_3way: Record<"v1" | "v2", string>;
      localization_exact: Record<"v1" | "v2", string>;
      localization_pm1: Record<"v1" | "v2", string>;
      localization_located_only: Record<"v1" | "v2", string>;
      category_agreement_at_exact_step: Record<"v1" | "v2", string>;
      resolved_flagged_invalid: { v1: string[]; v2: string[]; note: string };
    };
    residual_failure_mode: { id: string; evidence: string; diagnosis: string; disposition: string };
  };
}

export interface MetaData {
  updated: string;
  n_tasks: number;
  n_runs: number;
  agent_tokens_total: number | null;
  judge_tokens_recorded: number | null;
}
