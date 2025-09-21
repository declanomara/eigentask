import type { PageServerLoad } from './$types';

const API_URL = 'http://localhost:8000';

export const load: PageServerLoad = async ({ fetch }) => {
  const res = await fetch(`${API_URL}/tasks`, { credentials: 'include' });
  const tasks = res.ok ? await res.json() : [];
  return { tasks };
};
