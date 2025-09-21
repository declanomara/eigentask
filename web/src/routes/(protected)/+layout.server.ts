import { redirect } from '@sveltejs/kit';
import type { LayoutServerLoad } from './$types';

const API_URL = 'http://localhost:8000';

export const load: LayoutServerLoad = async ({ fetch, url }) => {
  const res = await fetch(`${API_URL}/auth/status`, { credentials: 'include' });
  if (!res.ok) {
    throw redirect(307, `${API_URL}/auth/login?return_to=${encodeURIComponent(url.href)}`);
  }
  const data = await res.json();
  if (!data?.authenticated) {
    throw redirect(307, `${API_URL}/auth/login?return_to=${encodeURIComponent(url.href)}`);
  }
  return { authenticated: true, user: data.user ?? null };
};
