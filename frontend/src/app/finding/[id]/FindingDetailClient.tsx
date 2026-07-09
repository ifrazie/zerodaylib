"use client";

import { useState, useEffect } from 'react';
import { Finding, SemanticMemoryItem, GovernanceStatus, AuditEvent } from '@/lib/types';
import {
  fetchFindingDetail,
  fetchSemanticMemory,
  fetchGovernanceStatus,
  fetchAuditTimeline
} from '@/lib/api';

interface FindingDetailClientProps {
  id: string;
}

export default function FindingDetailClient({ id }: FindingDetailClientProps) {
  const [finding, setFinding] = useState<Finding | null>(null);
  const [semanticMemory, setSemanticMemory] = useState<SemanticMemoryItem[]>([]);
  const [governance, setGovernance] = useState<GovernanceStatus | null>(null);
  const [auditTimeline, setAuditTimeline] = useState<AuditEvent[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // This route is served from a single exported shell (finding/_shell.html) that
  // CloudFront rewrites every /finding/<id> deep link to, so the build-time
  // `id` prop is a placeholder. Resolve the real id from the URL at runtime.
  const [resolvedId, setResolvedId] = useState<string>(id);
  useEffect(() => {
    if (typeof window !== 'undefined') {
      const segments = window.location.pathname.split('/').filter(Boolean);
      const last = segments[segments.length - 1];
      if (last && last !== '_shell' && last !== 'finding') {
        setResolvedId(decodeURIComponent(last));
      }
    }
  }, []);

  useEffect(() => {
    async function loadData() {
      try {
        setLoading(true);
        
        // Call real API endpoints
        const [findingData, semanticMemoryData, governanceData, auditTimelineData] = await Promise.all([
          fetchFindingDetail(resolvedId),
          fetchSemanticMemory(resolvedId),
          fetchGovernanceStatus(resolvedId),
          fetchAuditTimeline(resolvedId)
        ]);

        // Map API response to frontend types
        const finding = findingData ? {
          id: findingData.id,
          cve_id: findingData.cve_id,
          title: findingData.title || `CVE ${findingData.cve_id}`,
          description: findingData.exploitability_rationale || findingData.description || 'No description available',
          severity: ((findingData.severity || 'low').toLowerCase()) as 'low' | 'medium' | 'high' | 'critical',
          status: ((findingData.status || 'new').toLowerCase()) as 'new' | 'assigned' | 'investigating' | 'resolved',
          created_at: findingData.created_at,
          updated_at: findingData.updated_at,
        } : null;

        const semanticMemory = semanticMemoryData.map((item: any) => ({
          id: item.id,
          case_id: `FINDING-${item.id.substring(0, 6)}`,
          similarity_score: item.similarity_score ?? 0,
          title: item.title,
          summary: item.summary || 'No summary available',
          outcome: item.outcome || 'UNKNOWN',
          created_at: item.created_at,
        }));

        const governance: GovernanceStatus = governanceData ? {
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

        const auditTimeline = auditTimelineData.map((event: any) => ({
          id: event.id,
          finding_id: resolvedId,
          action: event.action,
          details: event.details,
          user: event.actor_id,
          timestamp: event.timestamp,
        }));

        setFinding(finding);
        setSemanticMemory(semanticMemory);
        setGovernance(governance);
        setAuditTimeline(auditTimeline);
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
    return <div className="flex justify-center items-center h-screen"><div className="animate-spin rounded-full h-16 w-16 border-t-4 border-b-4 border-primary"></div></div>;
  }

  if (error) {
    return <div className="container mx-auto px-4 py-8 text-red-600 text-center">{error}</div>;
  }

  if (!finding) {
    return <div className="container mx-auto px-4 py-8 text-center">Finding not found</div>;
  }

  const severityColors = {
    low: 'bg-green-100 text-green-800',
    medium: 'bg-blue-100 text-blue-800',
    high: 'bg-orange-100 text-orange-800',
    critical: 'bg-red-100 text-red-800',
  };

  const severityBadge = severityColors[finding.severity] || 'bg-gray-100 text-gray-800';

  return (
    <div className="container mx-auto px-4 py-8">
      <div className="bg-white rounded-lg shadow-lg p-6 mb-6">
        <div className="flex items-center justify-between mb-4">
          <div>
            <h1 className="text-2xl font-bold text-gray-900 flex items-center gap-2">
              <span>{finding.title}</span>
            </h1>
            <p className="text-gray-600 mt-2">CVE: {finding.cve_id}</p>
          </div>
          <div className="flex items-center gap-4">
            <span className={`px-3 py-1 rounded-full text-sm font-medium ${severityBadge}`}>
              {finding.severity.toUpperCase()}
            </span>
            <span className="px-3 py-1 rounded-full text-sm font-medium bg-yellow-100 text-yellow-800">
              {finding.status.toUpperCase()}
            </span>
          </div>
        </div>

        <div className="border-t border-gray-200 pt-4">
          <div className="prose max-w-none">
            <h3 className="font-semibold text-gray-900 mb-2">Description</h3>
            <p className="text-gray-700">{finding.description}</p>
          </div>
        </div>
      </div>

      {/* Semantic Memory Section */}
      <div className="bg-white rounded-lg shadow-lg p-6 mb-6">
        <div className="flex items-center justify-between mb-4">
          <h2 className="text-xl font-semibold text-gray-900">Similar Past Findings from Semantic Memory</h2>
          <span className="bg-gray-100 text-gray-700 px-3 py-1 rounded-full text-sm">
            Distributed Vector Indexing (CockroachDB)
          </span>
        </div>

        {semanticMemory.length === 0 ? (
          <div className="text-gray-500 italic">No similar findings retrieved from memory.</div>
        ) : (
          <div className="space-y-4">
            {semanticMemory.map((item) => (
              <div key={item.id} className="border border-gray-200 rounded-lg p-4">
                <div className="flex items-center justify-between mb-2">
                  <h3 className="font-medium text-gray-900">{item.title}</h3>
                  <span className="bg-blue-100 text-blue-800 px-2 py-1 rounded text-sm">
                    Similarity: {(item.similarity_score * 100).toFixed(1)}%
                  </span>
                </div>
                <p className="text-gray-600 text-sm mb-2">{item.summary}</p>
                <div className="flex gap-4 text-sm text-gray-500">
                  <span>Case ID: {item.case_id}</span>
                  <span>Outcome: {item.outcome}</span>
                  <span>Date: {new Date(item.created_at).toLocaleDateString()}</span>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>

      {/* Governance Decision */}
      <div className="bg-white rounded-lg shadow-lg p-6 mb-6">
        <div className="flex items-center justify-between mb-4">
          <h2 className="text-xl font-semibold text-gray-900">Governance Decision Status</h2>
          <span className="px-3 py-1 rounded-full text-sm font-medium bg-blue-100 text-blue-800">
            {governance?.state.toUpperCase().replace('_', ' ')}
          </span>
        </div>

        <div className="prose max-w-none">
          <p className="text-gray-700 mb-4">
            {governance?.state === 'unreviewed' && 'This finding has been ingested and awaits governance review.'}
            {governance?.state === 'under_review' && `Currently under review by ${governance.reviewer || 'the security team'}.`}
            {governance?.state === 'approved' && 'This finding has been approved according to governance policies.'}
            {governance?.state === 'rejected' && 'This finding was rejected or closed by governance.'}
            {governance?.state === 'manual_review' && 'Policy evaluation requires manual review before remediation can proceed.'}
            {governance?.state === 'allow' && 'Policy evaluation permits automated remediation for this finding.'}
            {governance?.state === 'deny' && 'Policy evaluation denies remediation for this finding.'}
          </p>

          {governance?.decision && (
            <div className="mt-4 p-4 bg-gray-50 rounded-lg">
              <h4 className="font-semibold text-gray-900 mb-2">Decision</h4>
              <p className="text-gray-700">{governance.decision}</p>
            </div>
          )}

          <div className="mt-4">
            <h4 className="font-semibold text-gray-900 mb-2">Policy Feedback</h4>
            {governance?.policy_feedbacks.length === 0 ? (
              <p className="text-gray-500 italic">No policy feedback has been applied yet.</p>
            ) : (
              <div className="space-y-2">
                {governance?.policy_feedbacks.map((feedback) => (
                  <div key={feedback.id} className="flex justify-between items-center p-2 bg-white border border-gray-200 rounded">
                    <div>
                      <span className="font-mono text-sm text-blue-600">{feedback.policy_name}</span>
                      <span className="text-gray-600 ml-2">- {feedback.evaluation}</span>
                    </div>
                    <span className={`text-sm font-medium ${feedback.score >= 0.9 ? 'text-green-600' : feedback.score >= 0.7 ? 'text-orange-600' : 'text-red-600'}`}>
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
      <div className="bg-white rounded-lg shadow-lg p-6">
        <div className="flex items-center justify-between mb-4">
          <h2 className="text-xl font-semibold text-gray-900">Audit Timeline</h2>
          <span className="bg-gray-100 text-gray-700 px-3 py-1 rounded-full text-sm">
            Complete workflow trace (CockroachDB)
          </span>
        </div>

        {auditTimeline.length === 0 ? (
          <div className="text-gray-500 italic">No audit events recorded for this finding.</div>
        ) : (
          <div className="border-l-2 border-gray-300 pl-6">
            {auditTimeline.map((event, index) => (
              <div key={event.id} className={`relative pb-6 ${index < auditTimeline.length - 1 ? 'border-b border-gray-200' : ''}`}>
                <div className="absolute -left-12 top-0 w-4 h-4 rounded-full" style={{ backgroundColor: getTimelineColor(event.action) }}></div>
                <div className="flex justify-between items-start mb-2">
                  <div>
                    <h4 className="text-sm font-semibold text-blue-600">{event.action}</h4>
                    <p className="text-sm text-gray-600">{event.details}</p>
                  </div>
                  <div className="text-right">
                    <p className="text-xs text-gray-500">by {event.user}</p>
                    <p className="text-xs text-gray-500 mt-1">
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
      CREATED: '#3B82F6',
      ASSIGNED: '#2563EB',
      STATUS_CHANGED: '#1D4ED8',
      SEMANTIC_MEMORY_QUERY: '#F59E0B',
      POLICY_EVALUATION: '#10B981',
      OTHER: '#64748B',
    };
    return colors[action] || colors.OTHER;
  }
}
