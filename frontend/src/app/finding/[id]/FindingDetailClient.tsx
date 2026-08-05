"use client";

import { useState, useEffect } from 'react';
import { Badge, Mono } from '@/components/ui';
import {
  fetchFindingDetail,
  fetchSemanticMemory,
  fetchGovernanceStatus,
  fetchAuditTimeline,
} from '@/lib/api';

type Finding = {
  id: string;
  cve_id: string;
  title: string;
  description: string;
  severity: 'low' | 'medium' | 'high' | 'critical';
  status: 'new' | 'assigned' | 'investigating' | 'resolved';
  created_at: string;
  updated_at: string;
};

type SemanticMemoryItem = {
  id: string;
  case_id: string;
  similarity_score: number;
  title: string;
  summary: string;
  outcome: string;
  created_at: string;
};

type PolicyFeedback = {
  id: string;
  policy_name: string;
  evaluation: string;
  score: number;
};

type GovernanceStatus = {
  finding_id: string;
  state: 'unreviewed' | 'under_review' | 'approved' | 'rejected' | 'manual_review' | 'allow' | 'deny';
  decision: string | null;
  reviewer: string | null;
  reviewed_at: string | null;
  policy_feedbacks: PolicyFeedback[];
};

type AuditEvent = {
  id: string;
  finding_id: string;
  action: string;
  details: string;
  user: string;
  timestamp: string;
};

interface FindingDetailClientProps {
  id: string;
}

export default function FindingDetailClient({ id: resolvedId }: FindingDetailClientProps) {
  const [finding, setFinding] = useState<Finding | null>(null);
  const [semanticMemory, setSemanticMemory] = useState<SemanticMemoryItem[]>([]);
  const [governance, setGovernance] = useState<GovernanceStatus | null>(null);
  const [auditTimeline, setAuditTimeline] = useState<AuditEvent[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    async function loadData() {
      if (!resolvedId) return;

      try {
        setLoading(true);
        const [findingData, semanticMemoryData, governanceData, auditTimelineData] = await Promise.all([
          fetchFindingDetail(resolvedId),
          fetchSemanticMemory(resolvedId),
          fetchGovernanceStatus(resolvedId),
          fetchAuditTimeline(resolvedId)
        ]);

        const mappedFinding = findingData ? {
          id: findingData.id,
          cve_id: findingData.cve_id,
          title: findingData.title || findingData.cve_id || 'Security Finding',
          description: findingData.exploitability_rationale || findingData.description || 'No description available',
          severity: ((findingData.severity || 'low').toLowerCase()) as 'low' | 'medium' | 'high' | 'critical',
          status: ((findingData.status || 'new').toLowerCase()) as 'new' | 'assigned' | 'investigating' | 'resolved',
          created_at: findingData.created_at,
          updated_at: findingData.updated_at,
        } : null;

        const mappedSemanticMemory = semanticMemoryData.map((item: any) => ({
          id: item.id,
          case_id: `FINDING-${item.id.substring(0, 6)}`,
          similarity_score: item.similarity_score ?? 0,
          title: item.title,
          summary: item.summary || 'No summary available',
          outcome: item.outcome || 'UNKNOWN',
          created_at: item.created_at,
        }));

        const mappedGovernance: GovernanceStatus = governanceData ? {
          finding_id: resolvedId,
          state: (governanceData.state || 'unreviewed') as GovernanceStatus['state'],
          decision: governanceData.decision || null,
          reviewer: governanceData.reviewer || 'sec-reviewers@company.com',
          reviewed_at: governanceData.reviewed_at || null,
          policy_feedbacks: governanceData.policy_feedbacks || [],
        } : {
          finding_id: resolvedId,
          state: 'unreviewed',
          decision: null,
          reviewer: 'sec-reviewers@company.com',
          reviewed_at: null,
          policy_feedbacks: [],
        };

        const mappedAuditTimeline = auditTimelineData.map((event: any) => ({
          id: event.id,
          finding_id: resolvedId,
          action: event.action,
          details: event.details,
          user: event.actor_id,
          timestamp: event.timestamp,
        }));

        setFinding(mappedFinding);
        setSemanticMemory(mappedSemanticMemory);
        setGovernance(mappedGovernance);
        setAuditTimeline(mappedAuditTimeline);
        setLoading(false);
      } catch (err) {
        setError('Failed to load finding data');
        setLoading(false);
        console.error('Error loading data:', err);
      }
    }

    loadData();
  }, [resolvedId]);

  if (loading) {
    return (
      <div className="flex justify-center items-center h-screen">
        <div
          className="animate-spin rounded-full h-16 w-16 border-t-4 border-b-4"
          style={{
            borderTopColor: 'var(--color-accent-fg)',
            borderBottomColor: 'var(--color-accent-fg)',
          }}
        />
      </div>
    );
  }

  if (error) {
    return <div className="container mx-auto px-4 py-8 text-red-600 text-center">{error}</div>;
  }

  if (!finding) {
    return <div className="container mx-auto px-4 py-8 text-center">Finding not found</div>;
  }

  return (
    <div className="container mx-auto px-4 py-8">
      {/* Findings Detail card */}
      <div className="bg-[var(--color-bg-subtle)] border border-[var(--color-border-default)] rounded-lg p-6 mb-6">
        <div className="flex items-center justify-between mb-4">
          <div>
            <h1 className="text-2xl font-bold text-[var(--color-fg-default)] flex items-center gap-2">
              <span>{finding.title}</span>
            </h1>
            {finding.title !== finding.cve_id && (
              <p className="text-[var(--color-fg-muted)] mt-2">CVE: {finding.cve_id}</p>
            )}
          </div>
          <div className="flex items-center gap-4">
            <Badge variant={finding.severity} emphasis />
            <Badge variant="neutral" emphasis>{finding.status}</Badge>
          </div>
        </div>

        <div className="border-t border-[var(--color-border-default)] pt-4">
          <div className="prose max-w-none">
            <h3 className="font-semibold text-[var(--color-fg-default)] mb-2">Description</h3>
            <p className="text-[var(--color-fg-muted)]">{finding.description}</p>
          </div>
        </div>
      </div>

      {/* Semantic Memory Section */}
      <div className="bg-[var(--color-bg-subtle)] border border-[var(--color-border-default)] rounded-lg p-6 mb-6">
        <div className="flex items-center justify-between mb-4">
          <h2 className="text-xl font-semibold text-[var(--color-fg-default)]">Similar Past Findings from Semantic Memory</h2>
          <span className="bg-[var(--color-bg-canvas)] text-[var(--color-fg-muted)] border border-[var(--color-border-default)] px-3 py-1 rounded-full text-sm">
            Distributed Vector Indexing (CockroachDB)
          </span>
        </div>

        {semanticMemory.length === 0 ? (
          <div className="text-[var(--color-fg-subtle)] italic">No similar findings retrieved from memory.</div>
        ) : (
          <div className="space-y-4">
            {semanticMemory.map((item) => (
              <div key={item.id} className="border border-[var(--color-border-muted)] bg-[var(--color-bg-default)] rounded-lg p-4">
                <div className="flex items-center justify-between mb-2">
                  <h3 className="font-medium text-[var(--color-fg-default)]">{item.title}</h3>
                  <span className="bg-[var(--color-accent-subtle)] text-[var(--color-accent-fg)] border border-[var(--color-accent-muted)] font-mono px-2 py-0.5 rounded text-xs">
                    Similarity: {(item.similarity_score * 100).toFixed(1)}%
                  </span>
                </div>
                <p className="text-[var(--color-fg-muted)] text-sm mb-2">{item.summary}</p>
                <div className="flex flex-wrap gap-4 text-xs text-[var(--color-fg-subtle)]">
                  <span>Case ID: {item.case_id}</span>
                  <span className="flex items-center gap-1">
                    Outcome: <Badge variant="neutral">{item.outcome}</Badge>
                  </span>
                  <span>Date: {new Date(item.created_at).toLocaleDateString()}</span>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>

      {/* Governance Decision */}
      <div className="bg-[var(--color-bg-subtle)] border border-[var(--color-border-default)] rounded-lg p-6 mb-6">
        <div className="flex items-center justify-between mb-4">
          <h2 className="text-xl font-semibold text-[var(--color-fg-default)]">Governance Decision Status</h2>
          <Badge variant={(governance?.state || 'unreviewed') as any} emphasis />
        </div>

        <div className="prose max-w-none">
          <p className="text-[var(--color-fg-muted)] mb-4">
            {governance?.state === 'unreviewed' && 'This finding has been ingested and awaits governance review.'}
            {governance?.state === 'under_review' && `Currently under review by ${governance.reviewer || 'the security team'}.`}
            {governance?.state === 'approved' && 'This finding has been approved according to governance policies.'}
            {governance?.state === 'rejected' && 'This finding was rejected or closed by governance.'}
            {governance?.state === 'manual_review' && 'Policy evaluation requires manual review before remediation can proceed.'}
            {governance?.state === 'allow' && 'Policy evaluation permits automated remediation for this finding.'}
            {governance?.state === 'deny' && 'Policy evaluation denies remediation for this finding.'}
          </p>

          {governance?.decision && (
            <div className="mt-4 p-4 bg-[var(--color-bg-default)] border border-[var(--color-border-muted)] rounded-lg">
              <h4 className="font-semibold text-[var(--color-fg-default)] mb-2">Decision Rationale</h4>
              <p className="text-[var(--color-fg-muted)]">{governance.decision}</p>
            </div>
          )}

          <div className="mt-4">
            <h4 className="font-semibold text-[var(--color-fg-default)] mb-2">Policy Feedback</h4>
            {governance?.policy_feedbacks.length === 0 ? (
              <p className="text-[var(--color-fg-subtle)] italic">No policy feedback has been applied yet.</p>
            ) : (
              <div className="space-y-2">
                {governance?.policy_feedbacks.map((feedback) => (
                  <div key={feedback.id} className="flex justify-between items-center p-2 bg-[var(--color-bg-default)] border border-[var(--color-border-muted)] rounded">
                    <div>
                      <span className="font-mono text-sm text-[var(--color-accent-fg)]">{feedback.policy_name}</span>
                      <span className="text-[var(--color-fg-muted)] ml-2">- {feedback.evaluation}</span>
                    </div>
                    <span className={`text-sm font-medium ${feedback.score >= 0.9 ? 'text-[var(--color-success-fg)]' : feedback.score >= 0.7 ? 'text-[var(--color-attention-fg)]' : 'text-[var(--color-danger-fg)]'}`}>
                      Score: {(feedback.score * 100).toFixed(1)}%
                    </span>
                  </div>
                ))}
              </div>
            )}
          </div>
        </div>
      </div>

      {/* Audit Timeline */}
      <div className="bg-[var(--color-bg-subtle)] border border-[var(--color-border-default)] rounded-lg p-6">
        <div className="flex items-center justify-between mb-4">
          <h2 className="text-xl font-semibold text-[var(--color-fg-default)]">Audit Timeline</h2>
          <span className="bg-[var(--color-bg-canvas)] text-[var(--color-fg-muted)] border border-[var(--color-border-default)] px-3 py-1 rounded-full text-sm">
            Complete workflow trace (CockroachDB)
          </span>
        </div>

        {auditTimeline.length === 0 ? (
          <div className="text-[var(--color-fg-subtle)] italic">No audit events recorded for this finding.</div>
        ) : (
          <div className="border-l-2 border-[var(--color-border-default)] pl-6">
            {auditTimeline.map((event, index) => (
              <div key={event.id} className={`relative pb-6 ${index < auditTimeline.length - 1 ? 'border-b border-[var(--color-border-muted)]' : ''}`}>
                <div className="absolute -left-[31px] top-1.5 w-3 h-3 rounded-full" style={{ backgroundColor: getTimelineColor(event.action) }}></div>
                <div className="flex justify-between items-start mb-2">
                  <div>
                    <h4 className="text-sm font-semibold text-[var(--color-accent-fg)]">{event.action}</h4>
                    <p className="text-sm text-[var(--color-fg-muted)]">{event.details}</p>
                  </div>
                  <div className="text-right">
                    <p className="text-xs text-[var(--color-fg-subtle)] font-mono">by {event.user}</p>
                    <p className="text-xs text-[var(--color-fg-subtle)] mt-1">
                      {new Date(event.timestamp).toLocaleString()}
                    </p>
                  </div>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );

  function getTimelineColor(action: string): string {
    const colors: Record<string, string> = {
      CREATED: 'var(--color-accent-fg)',
      ASSIGNED: 'var(--color-accent-fg)',
      STATUS_CHANGED: 'var(--color-attention-fg)',
      SEMANTIC_MEMORY_QUERY: 'var(--color-success-fg)',
      POLICY_EVALUATION: 'var(--color-done-fg)',
      OTHER: 'var(--color-fg-subtle)',
    };
    return colors[action] || colors.OTHER;
  }
}
