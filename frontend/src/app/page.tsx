"use client";

import { useState, useEffect } from 'react';
import { fetchFindings } from '../lib/api';

type FindingRow = {
  id: string;
  cve_id: string;
  status: string;
  severity: string;
  exploitability_score: number | null;
  owner_team: string | null;
  decision_state: string | null;
  created_at: string | null;
  updated_at: string | null;
};

const severityColors: Record<string, string> = {
  low: 'bg-green-100 text-green-800',
  medium: 'bg-blue-100 text-blue-800',
  high: 'bg-orange-100 text-orange-800',
  critical: 'bg-red-100 text-red-800',
};

const decisionColors: Record<string, string> = {
  pending: 'bg-yellow-100 text-yellow-800',
  allow: 'bg-green-100 text-green-800',
  deny: 'bg-red-100 text-red-800',
  manual_review: 'bg-purple-100 text-purple-800',
};

export default function FindingsListPage() {
  const [findings, setFindings] = useState<FindingRow[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // Read filters from the URL client-side (this is a static export — there is
  // no server searchParams). window is only available after mount.
  const [statusFilter, setStatusFilter] = useState('all');
  const [severityFilter, setSeverityFilter] = useState('all');

  useEffect(() => {
    const params = new URLSearchParams(window.location.search);
    setStatusFilter(params.get('status') || 'all');
    setSeverityFilter(params.get('severity') || 'all');
  }, []);

  useEffect(() => {
    async function loadFindings() {
      try {
        setLoading(true);
        const data: FindingRow[] = await fetchFindings();

        const filtered = data.filter((finding) => {
          const status = (finding.status || '').toLowerCase();
          const severity = (finding.severity || '').toLowerCase();
          const statusMatch = statusFilter === 'all' || status === statusFilter.toLowerCase();
          const severityMatch = severityFilter === 'all' || severity === severityFilter.toLowerCase();
          return statusMatch && severityMatch;
        });

        setFindings(filtered);
        setLoading(false);
      } catch (err) {
        setError('Failed to load findings');
        setLoading(false);
        console.error('Error loading findings:', err);
      }
    }

    loadFindings();
  }, [statusFilter, severityFilter]);

  const statusCounts = findings.reduce((acc, finding) => {
    const s = (finding.status || 'unknown').toLowerCase();
    acc[s] = (acc[s] || 0) + 1;
    return acc;
  }, {} as Record<string, number>);

  const severityCounts = findings.reduce((acc, finding) => {
    const s = (finding.severity || 'unknown').toLowerCase();
    acc[s] = (acc[s] || 0) + 1;
    return acc;
  }, {} as Record<string, number>);

  if (loading) {
    return <div className="flex justify-center items-center h-64"><div className="animate-spin rounded-full h-16 w-16 border-t-4 border-b-4" style={{ borderTopColor: 'var(--color-accent-fg)', borderBottomColor: 'var(--color-accent-fg)' }}></div></div>;
  }

  if (error) {
    return <div className="container mx-auto px-4 py-8 text-red-600 text-center">{error}</div>;
  }

  return (
    <div>
      <div className="flex justify-between items-center mb-6">
        <h1 className="text-2xl font-bold text-gray-900">Findings Dashboard</h1>
        <div className="bg-gray-100 text-gray-700 px-3 py-1 rounded-full text-sm">
          Zero Day Librarian - Demo Dashboard
        </div>
      </div>

      {/* Filters */}
      <div className="flex flex-wrap gap-4 mb-6">
        <div className="flex items-center gap-2">
          <span className="text-sm font-medium text-gray-600">Status:</span>
          <select
            className="px-3 py-1 rounded-md border border-[var(--color-border-default)] bg-[var(--color-bg-subtle)] text-[var(--color-fg-default)] focus:ring-2 focus:ring-[var(--color-accent-fg)] focus:border-transparent"
            value={statusFilter}
            onChange={(e) => {
              const params = new URLSearchParams();
              if (e.target.value !== 'all') params.set('status', e.target.value);
              if (severityFilter !== 'all') params.set('severity', severityFilter);
              window.location.search = params.toString();
            }}
          >
            <option value="all">All statuses</option>
            {Object.entries(statusCounts).map(([status, count]) => (
              <option key={status} value={status}>{status.charAt(0).toUpperCase() + status.slice(1)} ({count})</option>
            ))}
          </select>
        </div>

        <div className="flex items-center gap-2">
          <span className="text-sm font-medium text-gray-600">Severity:</span>
          <select
            className="px-3 py-1 rounded-md border border-[var(--color-border-default)] bg-[var(--color-bg-subtle)] text-[var(--color-fg-default)] focus:ring-2 focus:ring-[var(--color-accent-fg)] focus:border-transparent"
            value={severityFilter}
            onChange={(e) => {
              const params = new URLSearchParams();
              if (statusFilter !== 'all') params.set('status', statusFilter);
              if (e.target.value !== 'all') params.set('severity', e.target.value);
              window.location.search = params.toString();
            }}
          >
            <option value="all">All severities</option>
            {Object.entries(severityCounts).map(([severity, count]) => (
              <option key={severity} value={severity}>{severity.charAt(0).toUpperCase() + severity.slice(1)} ({count})</option>
            ))}
          </select>
        </div>
      </div>

      {/* Findings List */}
      {findings.length === 0 ? (
        <div className="text-center py-12 text-gray-500">
          <p className="mb-4">No findings match the current filters.</p>
          <button
            className="px-4 py-2 bg-[var(--color-accent-emphasis)] text-[var(--color-fg-on-emphasis)] rounded-md hover:bg-[var(--color-accent-fg)]"
            onClick={() => (window.location.search = '')}
          >
            Clear filters
          </button>
        </div>
      ) : (
        <div className="bg-white rounded-lg shadow-lg overflow-hidden">
          <table className="w-full">
            <thead className="bg-gray-50">
              <tr>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">CVE</th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Severity</th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Status</th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Governance</th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Owner</th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Created</th>
              </tr>
            </thead>
            <tbody className="bg-white divide-y divide-gray-200">
              {findings.map((finding) => {
                const severity = (finding.severity || 'unknown').toLowerCase();
                const decision = (finding.decision_state || 'pending').toLowerCase();
                return (
                  <tr key={finding.id} className="hover:bg-gray-50">
                    <td className="px-6 py-4 whitespace-nowrap text-sm">
                      <a href={`/finding/${finding.id}`} className="text-blue-600 hover:underline font-medium">
                        {finding.cve_id}
                      </a>
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap text-sm">
                      <span className={`px-2 py-1 rounded-full text-xs font-medium ${severityColors[severity] || 'bg-gray-100 text-gray-800'}`}>
                        {(finding.severity || 'UNKNOWN').toUpperCase()}
                      </span>
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-900">
                      {(finding.status || 'unknown').toUpperCase()}
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap text-sm">
                      <span className={`px-2 py-1 rounded-full text-xs font-medium ${decisionColors[decision] || 'bg-gray-100 text-gray-800'}`}>
                        {decision.replace('_', ' ').toUpperCase()}
                      </span>
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">{finding.owner_team || '—'}</td>
                    <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                      {finding.created_at ? new Date(finding.created_at).toLocaleDateString() : '—'}
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}
