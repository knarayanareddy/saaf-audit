export type Severity = "low" | "medium" | "high" | "critical";

export const SEVERITY_ORDER: Record<Severity, number> = {
  low: 0,
  medium: 1,
  high: 2,
  critical: 3,
};

export interface Finding {
  ruleId: string;
  title: string;
  severity: Severity;
  repo: string;
  file: string; // path relative to the repository root
  line: number; // 1-indexed
  column: number; // 1-indexed
  snippet: string; // already sanitized for terminal display
  detail?: string;
  llmReview?: LlmReview;
}

export interface LlmReview {
  verdict: "malicious" | "suspicious" | "benign";
  confidence: number; // 0..1
  explanation: string;
}

/** A match produced by a rule, before repo/file metadata is attached. */
export interface RuleMatch {
  index: number; // character offset in the file content
  length: number;
  detail?: string;
}

export interface Rule {
  id: string;
  title: string;
  severity: Severity;
  /** Optional filter on file path (relative, forward slashes). */
  appliesTo?: (path: string) => boolean;
  match: (content: string) => RuleMatch[];
}
