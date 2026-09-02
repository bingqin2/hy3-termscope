export type ConfigId = "hy3-react" | "hy3-react-verify" | "hy3-oneshot";

export interface LeaderboardRow {
  config_id: ConfigId;
  label: string;
  mean_score: number;
  resolve_rate: number;
  tasks_won: number;
}

export interface LeaderboardData {
  sample: boolean;
  updated: string;
  rows: LeaderboardRow[];
}

export interface TaskRow {
  task_id: string;
  name: string;
  layer: "L1" | "L2" | "L3" | "L4";
  layer_label: string;
  difficulty: 1 | 2 | 3;
  backend: string;
  trap: string;
  scores: Record<ConfigId, number>;
}

export interface TasksData {
  sample: boolean;
  rows: TaskRow[];
}

export type Severity = "critical" | "high" | "medium";

export interface FailurePattern {
  error_type: string;
  label: string;
  severity: Severity;
  count: number;
}

export interface FailurePatternsData {
  sample: boolean;
  rows: FailurePattern[];
}

export interface CheckResult {
  id: string;
  pass: boolean;
}

export interface RunStep {
  n: number;
  thought: string;
  command: string;
  observation: string;
  exit_code: number;
}

export interface Run {
  run_id: string;
  task_id: string;
  task_name: string;
  config_id: ConfigId;
  outcome: "resolved" | "unresolved" | "inconclusive";
  process: "valid" | "partial" | "invalid";
  score: number;
  first_error_step: number | null;
  error_types: string[];
  finding: string;
  checks: CheckResult[];
  steps: RunStep[];
}

export interface RunsData {
  sample: boolean;
  runs: Run[];
}

export interface Ratio {
  num: number;
  den: number;
}

export interface ValidationData {
  sample: boolean;
  localization_exact: Ratio;
  localization_pm1: Ratio;
  false_positive_rate: Ratio;
  discriminative: string;
  consistency: string;
}
