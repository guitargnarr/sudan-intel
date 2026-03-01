const BASE = '';

export async function fetchAPI(endpoint) {
  const res = await fetch(`${BASE}${endpoint}`);
  if (!res.ok) throw new Error(`API error: ${res.status}`);
  return res.json();
}

export const api = {
  dashboard: () => fetchAPI('/api/dashboard'),
  regions: () => fetchAPI('/api/regions'),
  region: (code) => fetchAPI(`/api/regions/${code}`),
  conflict: (admin1) => fetchAPI(`/api/conflict${admin1 ? `?admin1_code=${admin1}` : ''}`),
  displacement: (admin1) => fetchAPI(`/api/displacement${admin1 ? `?admin1_code=${admin1}` : ''}`),
  foodSecurity: (admin1) => fetchAPI(`/api/food-security${admin1 ? `?admin1_code=${admin1}` : ''}`),
  news: (limit = 20) => fetchAPI(`/api/news?limit=${limit}`),
  synthesis: (scope = 'national', region = null) =>
    fetchAPI(`/api/synthesis?scope=${scope}${region ? `&region=${region}` : ''}`),
  sources: () => fetchAPI('/api/sources'),
};
