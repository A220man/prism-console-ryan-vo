export type CommandRecord = {
  path: string;
  surface_id: string | null;
  group: string;
  verb: string;
  handler: string;
  kind: string;
  summary: string;
  method: string | null;
  route: string | null;
  executable: boolean;
  reasons: string[];
  argv: string[];
  invocation: string;
  bound: Record<string, string>;
};

export type GeneratorReport = {
  proposed: number;
  executable: number;
  surfaces_covered: number;
  coverage: number;
  correctness: number;
  commands?: CommandRecord[];
};

export type Analysis = {
  id: number;
  application: string;
  executable_name: string;
  created_at: string;
  surface_count: number;
  notices: string[];
  grounded: GeneratorReport;
  thin: GeneratorReport;
};

export type AnalysisList = {
  items: Analysis[];
  total: number;
  limit: number;
  offset: number;
};

export type Score = {
  true_positives: number;
  predicted: number;
  gold: number;
  precision: number;
  recall: number;
  f1: number;
};

export type CaseScore = {
  predicted: string[];
  false_positives: string[];
  false_negatives: string[];
  true_positives: number;
  precision: number;
  recall: number;
  f1: number;
};

export type EvaluationCase = {
  name: string;
  gold: string[];
  grounded: CaseScore;
  thin: CaseScore;
};

export type EvaluationReport = {
  case_count: number;
  convention: string;
  grounded: Score;
  thin: Score;
  cases: EvaluationCase[];
  failure_cases: string[];
};

export type ExportPayload = {
  application: string;
  executable_name: string;
  commands: CommandRecord[];
};
