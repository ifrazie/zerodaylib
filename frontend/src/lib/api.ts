// When NEXT_PUBLIC_API_BASE_URL is defined (including an empty string), honor it
// verbatim. An empty string yields same-origin relative calls (e.g. `/api/findings`),
// which is how the production CloudFront deployment routes `/api/*` to the backend.
// Only fall back to the local dev server when the variable is entirely undefined.
export const API_BASE_URL =
  process.env.NEXT_PUBLIC_API_BASE_URL ?? 'http://localhost:8000';

export async function fetchFindings() {
  try {
    const response = await fetch(`${API_BASE_URL}/api/findings`);
    if (!response.ok) {
      throw new Error('Failed to fetch findings');
    }
    return await response.json();
  } catch (error) {
    console.error('Error fetching findings:', error);
    return [];
  }
}

export async function fetchFindingDetail(id: string) {
  try {
    const response = await fetch(`${API_BASE_URL}/api/findings/${id}`);
    if (!response.ok) {
      throw new Error('Failed to fetch finding detail');
    }
    return await response.json();
  } catch (error) {
    console.error('Error fetching finding detail:', error);
    return null;
  }
}

export async function fetchSemanticMemory(id: string) {
  try {
    const response = await fetch(`${API_BASE_URL}/api/semantic-memory/${id}`);
    if (!response.ok) {
      throw new Error('Failed to fetch semantic memory');
    }
    return await response.json();
  } catch (error) {
    console.error('Error fetching semantic memory:', error);
    return [];
  }
}

export async function fetchGovernanceStatus(id: string) {
  try {
    const response = await fetch(`${API_BASE_URL}/api/governance/${id}`);
    if (!response.ok) {
      throw new Error('Failed to fetch governance status');
    }
    return await response.json();
  } catch (error) {
    console.error('Error fetching governance status:', error);
    return null;
  }
}

export async function fetchAuditTimeline(id: string) {
  try {
    const response = await fetch(`${API_BASE_URL}/api/audit/${id}`);
    if (!response.ok) {
      throw new Error('Failed to fetch audit timeline');
    }
    return await response.json();
  } catch (error) {
    console.error('Error fetching audit timeline:', error);
    return [];
  }
}