import type { PageServerLoad } from './$types';
import { env } from '$env/dynamic/private';

const API_URL = env.API_ORIGIN ?? 'http://localhost:8000';

export const load: PageServerLoad = async ({ fetch, url, request }) => {
  try {
    const endpoint = `${API_URL}/tasks`;
    const res = await fetch(endpoint, { credentials: 'include' });
    if (!res.ok) {
      console.error('Upstream responded non-OK', {
        endpoint,
        status: res.status,
        statusText: res.statusText
      });
    }
    const tasks = res.ok ? await res.json() : [];
    return { tasks };
  } catch (err: unknown) {
    const errObj = err as any;
    console.error('Upstream fetch failed', {
      api_origin: API_URL,
      path: '/tasks',
      method: 'GET',
      error: errObj?.message || String(errObj),
      stack: errObj?.stack
    });
    throw errObj;
  }
};
