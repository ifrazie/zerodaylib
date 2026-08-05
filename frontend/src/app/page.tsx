"use client";

import { useState, useEffect } from 'react';
import { fetchFindings } from '../lib/api';
import { Badge, DataTable, Mono } from '@/components/ui';
import type { Column } from '@/components/ui';

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

export default function FindingsListPage() {
  const [findings, setFindings] = useState<FindingRow[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

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
    return (
      <div className="flex justify-center items-center h-64">
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

  const columns: Column<FindingRow>[] = [
    {
      key: 'cve_id',
      header: 'CVE',
      cell: (row) => (
        <a href={`/finding/${row.id}`} className="hover:underline font-medium text-[var(--color-accent-fg)]">
          <Mono tone="accent">{row.cve_id}</Mono>
        </a>
      ),
    },
    {
      key: 'severity',
      header: 'Severity',
      cell: (row) => (
        <Badge variant={row.severity.toLowerCase() as any} />
      ),
    },
    {
      key: 'status',
      header: 'Status',
      cell: (row) => (
        <span className="font-mono text-xs uppercase text-[var(--color-fg-default)]">
          {row.status}
        </span>
      ),
    },
    {
      key: 'decision_state',
      header: 'Governance',
      cell: (row) => (
        <Badge variant={(row.decision_state || 'unreviewed').toLowerCase() as any} />
      ),
    },
    {
      key: 'owner_team',
      header: 'Owner',
      cell: (row) => (
        <Mono tone="muted">{row.owner_team || '—'}</Mono>
      ),
    },
    {
      key: 'created_at',
      header: 'Created',
      cell: (row) => (
        <span className="text-xs text-[var(--color-fg-muted)]">
          {row.created_at ? new Date(row.created_at).toLocaleDateString() : '—'}
        </span>
      ),
    },
  ];

  return (
    <div>
      <div className="flex justify-between items-center mb-6">
        <h1 className="text-2xl font-bold text-[var(--color-fg-default)]">Findings Dashboard</h1>
        <div className="bg-[var(--color-bg-subtle)] text-[var(--color-fg-muted)] border border-[var(--color-border-default)] px-3 py-1 rounded-full text-sm">
          Zero Day Librarian - Demo Dashboard
        </div>
      </div>

      {/* Filters */}
      <div className="flex flex-wrap gap-4 mb-6">
        <div className="flex items-center gap-2">
          <span className="text-sm font-medium text-[var(--color-fg-muted)]">Status:</span>
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
              <option key={status} value={status}>
                {status.charAt(0).toUpperCase() + status.slice(1)} ({count})
              </option>
            ))}
          </select>
        </div>

        <div className="flex items-center gap-2">
          <span className="text-sm font-medium text-[var(--color-fg-muted)]">Severity:</span>
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
              <option key={severity} value={severity}>
                {severity.charAt(0).toUpperCase() + severity.slice(1)} ({count})
              </option>
            ))}
          </select>
        </div>
      </div>

      {/* Findings List */}
      <DataTable
        columns={columns}
        rows={findings}
        rowKey={(row) => row.id}
        emptyState={
          <div className="text-center py-6 text-[var(--color-fg-muted)]">
            <p className="mb-4">No findings match the current filters.</p>
            <button
              className="px-4 py-2 bg-[var(--color-accent-emphasis)] text-[var(--color-fg-on-emphasis)] rounded-md hover:bg-[var(--color-accent-fg)]"
              onClick={() => (window.location.search = '')}
            >
              Clear filters
            </button>
          </div>
        }
      />
    </div>
  );
}
