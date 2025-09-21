import type { PageServerLoad } from './$types';
import { env } from '$env/dynamic/private';

const API_URL = env.API_ORIGIN ?? 'http://localhost:8000';

export const load: PageServerLoad = async ({ fetch }) => {
  const res = await fetch(`${API_URL}/tasks`, { credentials: 'include' });
  const tasks = res.ok ? await res.json() : [];
  return { tasks };
};
