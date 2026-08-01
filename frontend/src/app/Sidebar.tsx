"use client";

import { useState, useEffect } from 'react';
import { MetricTile } from '@/components/ui/MetricTile';
import { StatusDot } from '@/components/ui/StatusDot';
import { fetchSystemStatus, type SystemStatus } from '@/lib/api';

interface SidebarProps {
  children: React.ReactNode;
}

export default function Sidebar({ children }: SidebarProps) {
  const [sidebarOpen, setSidebarOpen] = useState(false);
  const [system, setSystem] = useState<SystemStatus | null>(null);

  useEffect(() => {
    fetchSystemStatus().then(setSystem);
  }, []);

  return (
    <div className="min-h-screen bg-gray-100">
      {/* Mobile sidebar toggle */}
      <div className="lg:hidden bg-white shadow-sm">
        <div className="container mx-auto px-4 py-2 flex justify-between items-center">
          <h1 className="text-lg font-semibold text-gray-900">Zero Day Librarian</h1>
          <button
            className="p-2 rounded-md text-gray-600 hover:bg-gray-100"
            onClick={() => setSidebarOpen(!sidebarOpen)}
          >
            <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 6h16M4 12h16M4 18h16" />
            </svg>
          </button>
        </div>
      </div>

      <div className="flex">
        {/* Sidebar */}
        <div className={"fixed inset-0 z-40 flex-none bg-white lg:static lg:bg-transparent lg:w-64 transition-all duration-300 ease-in-out " + (sidebarOpen ? "translate-x-0" : "-translate-x-full") + " lg:translate-x-0"}>
          <div className="lg:hidden p-4">
            <button
              className="p-2 rounded-md text-gray-600 hover:bg-gray-100"
              onClick={() => setSidebarOpen(false)}
            >
              <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
              </svg>
            </button>
          </div>

          <div className="h-screen overflow-y-auto p-4">
            <h1 className="text-xl font-bold text-gray-900 mb-2">Zero Day Librarian</h1>
            <p className="text-xs text-gray-500 mb-4">Hackathon Demo Dashboard</p>

            {system && (
              <div className="space-y-1 mb-4">
                <StatusDot status="healthy" label="Env" detail={system.environment} />
                <StatusDot status="healthy" label="Region" detail={system.region} />
                <StatusDot status="healthy" label="Version" detail={system.version} />
              </div>
            )}

            {system && (
              <div className="grid grid-cols-2 gap-2 mb-4">
                <MetricTile label="Findings" value={system.counts.findings ?? 0} />
                <MetricTile label="Critical" value={system.counts.findings_critical ?? 0} tone="critical" />
                <MetricTile label="Assets" value={system.counts.assets ?? 0} />
                <MetricTile label="Policies" value={system.counts.policies ?? 0} />
              </div>
            )}

            {system && (
              <div className="mb-4">
                <p className="px-1 text-xs font-semibold text-gray-500 uppercase mb-2">Pipeline</p>
                <div className="space-y-2">
                  <StatusDot
                    status={system.agents.ingest?.status ?? 'unknown'}
                    label="Ingest"
                    detail={String(system.agents.ingest?.events_total ?? 0) + ' events'}
                  />
                  <StatusDot
                    status={system.agents.semantic_memory?.status ?? 'unknown'}
                    label="Semantic Memory"
                    detail={String(system.agents.semantic_memory?.queries_total ?? 0) + ' queries'}
                  />
                  <StatusDot
                    status={system.agents.governance?.status ?? 'unknown'}
                    label="Governance"
                    detail={String(system.agents.governance?.auto_approval_pct ?? 0) + '% auto-approve'}
                  />
                </div>
              </div>
            )}

            {system && (
              <div className="mb-4">
                <p className="px-1 text-xs font-semibold text-gray-500 uppercase mb-2">Infrastructure</p>
                <div className="space-y-2">
                  <StatusDot
                    status={system.infrastructure.cockroachdb?.status ?? 'unknown'}
                    label="CockroachDB"
                    detail={String(system.infrastructure.cockroachdb?.nodes ?? 0) + ' nodes'}
                  />
                  <StatusDot
                    status={system.infrastructure.bedrock?.status ?? 'unknown'}
                    label="Bedrock"
                    detail={system.infrastructure.bedrock?.region ?? ''}
                  />
                  <StatusDot
                    status={system.infrastructure.agentcore?.status ?? 'unknown'}
                    label="AgentCore"
                    detail={String(system.infrastructure.agentcore?.agent_count ?? 0) + ' agents'}
                  />
                </div>
              </div>
            )}

            <nav className="space-y-1">
              <a
                href="/"
                className="flex items-center px-3 py-2 text-sm font-medium text-gray-700 rounded-md hover:bg-gray-100"
              >
                <svg className="w-5 h-5 mr-3" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 17v-2m3 2v-4m3 4v-6m2 10H7a2 2 0 01-2-2V7a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
                </svg>
                Findings Dashboard
              </a>

              <div className="pt-4 pb-2">
                <p className="px-3 text-xs font-semibold text-gray-500 uppercase">Workflow</p>
              </div>

              <div className="flex items-center px-3 py-2 text-sm font-medium text-gray-700 rounded-md">
                <svg className="w-5 h-5 mr-3" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 6.253v11.494m-9-5.747h18" />
                </svg>
                CVE Ingestion
              </div>

              <div className="flex items-center px-3 py-2 text-sm font-medium text-gray-700 rounded-md">
                <svg className="w-5 h-5 mr-3" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13.828 10.172a4 4 0 00-5.656 0l-4 4a4 4 0 105.656 5.656l1.102-1.101m-.758-4.899a4 4 0 005.656 0l4-4a4 4 0 00-5.656-5.656l-1.1 1.1" />
                </svg>
                Asset Linking
              </div>

              <div className="flex items-center px-3 py-2 text-sm font-medium text-green-600 rounded-md">
                <svg className="w-5 h-5 mr-3" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4.318 6.318a4.5 4.5 0 000 6.364L12 20.364l7.682-7.682a4.5 4.5 0 00-6.364-6.364L12 7.636l-1.318-1.318a4.5 4.5 0 00-6.364 0z" />
                </svg>
                <span className="flex items-center">
                  Semantic Memory
                  <span className="ml-2 bg-green-100 text-green-800 text-xs font-medium px-2 py-0.5 rounded-full">
                    Distributed Vector Index
                  </span>
                </span>
              </div>

              <div className="flex items-center px-3 py-2 text-sm font-medium text-gray-700 rounded-md">
                <svg className="w-5 h-5 mr-3" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 15v2m-6 4h12a2 2 0 002-2v-6a2 2 0 00-2-2H6a2 2 0 00-2 2v6a2 2 0 002 2zm10-10V7a4 4 0 00-8 0v4h8z" />
                </svg>
                Policy Evaluation
              </div>

              <div className="flex items-center px-3 py-2 text-sm font-medium text-gray-700 rounded-md">
                <svg className="w-5 h-5 mr-3" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
                </svg>
                Timeline Tracking
              </div>
            </nav>

            <div className="mt-8 pt-4 border-t border-gray-200">
              <div className="px-2 space-y-1">
                <a
                  href="https://www.cockroachlabs.com/docs/stable/"
                  target="_blank"
                  rel="noopener noreferrer"
                  className="flex items-center px-3 py-2 text-sm font-medium text-gray-600 rounded-md hover:bg-gray-100"
                >
                  <svg className="w-5 h-5 mr-3" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 6v6m0 0v6m0-6h6m-6 0H6" />
                  </svg>
                  CockroachDB Docs
                </a>

                <a
                  href="https://github.com/ifrazie/zerodaylib"
                  target="_blank"
                  rel="noopener noreferrer"
                  className="flex items-center px-3 py-2 text-sm font-medium text-gray-600 rounded-md hover:bg-gray-100"
                >
                  <svg className="w-5 h-5 mr-3" fill="currentColor" viewBox="0 0 24 24">
                    <path fillRule="evenodd" d="M12 2C6.477 2 2 6.477 2 12c0 4.418 2.865 8.168 6.839 9.49.5.092.682-.217.682-.482 0-.237-.009-.868-.014-1.703-2.782.605-3.369-1.343-3.369-1.343-.454-1.158-1.11-1.466-1.11-1.466-.908-.62.069-.608.069-.608 1.003.07 1.531 1.032 1.531 1.032.892 1.53 2.341 1.088 2.91.832.092-.647.35-1.088.636-1.338-2.22-.253-4.555-1.113-4.555-4.951 0-1.093.39-1.988 1.031-2.688-.103-.253-.446-1.272.098-2.65 0 0 .84-.27 2.75 1.026A9.564 9.564 0 0112 6.844c.85.004 1.705.115 2.504.337 1.909-1.296 2.747-1.027 2.747-1.027.546 1.379.203 2.398.1 2.651.64.7 1.03 1.595 1.03 2.688 0 3.848-2.338 4.695-4.566 4.942.359.309.678.92.678 1.852 0 1.338-.015 2.419-.015 2.747 0 .268.18.58.688.482A10.001 10.001 0 0022 12c0-5.523-4.477-10-10-10z" clipRule="evenodd" />
                  </svg>
                  GitHub Repository
                </a>
              </div>
            </div>
          </div>
        </div>

        {/* Main content */}
        <div className="flex-1">
          {/* Desktop header */}
          <header className="hidden lg:block bg-white shadow-sm">
            <div className="container mx-auto px-4 py-4 flex justify-between items-center">
              <h1 className="text-xl font-bold text-gray-900">Zero Day Librarian</h1>
              <div className="flex items-center gap-4">
                <span className="bg-gray-100 text-gray-700 px-3 py-1 rounded-full text-sm">
                  Hackathon Demo Dashboard
                </span>
              </div>
            </div>
          </header>

          <main className="container mx-auto px-4 py-8 lg:py-12">
            {children}
          </main>
        </div>
      </div>
    </div>
  );
}
