export type Finding = {
  id: string;
  cve_id: string;
  title: string;
  description: string;
  severity: 'low' | 'medium' | 'high' | 'critical';
  status: 'new' | 'assigned' | 'investigating' | 'resolved';
  created_at: string;
  updated_at: string;
};

export type SemanticMemoryItem = {
  id: string;
  case_id: string;
  similarity_score: number;
  title: string;
  summary: string;
  outcome: string;
  created_at: string;
};

export type GovernanceStatus = {
  finding_id: string;
  state: 'unreviewed' | 'under_review' | 'approved' | 'rejected' | 'allow' | 'deny' | 'manual_review';
  decision: string | null;
  reviewer: string | null;
  reviewed_at: string | null;
  policy_feedbacks: PolicyFeedback[];
};

export type PolicyFeedback = {
  id: string;
  policy_name: string;
  evaluation: string;
  score: number;
  created_at: string;
};

export type AuditEvent = {
  id: string;
  finding_id: string;
  action: string;
  details: string;
  user: string;
  timestamp: string;
};