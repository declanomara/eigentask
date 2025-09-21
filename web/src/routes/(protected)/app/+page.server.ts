import type { PageServerLoad } from './$types';
import { env } from '$env/dynamic/private';

const API_URL = env.API_ORIGIN ?? 'http://localhost:8000';

export const load: PageServerLoad = async ({ fetch, url, request }) => {
  try {
    const endpoint = `${API_URL}/tasks`;
    const cookie = request.headers.get('cookie') ?? '';

    // Diagnostics about incoming request
    const host = request.headers.get('host');
    console.info('SSR load diagnostics', {
      page: '/app',
      host,
      api_origin: API_URL,
      cookie_present: cookie.length > 0,
      cookie_length: cookie.length,
      cookie_has_sid: /(^|;\s*)sid=/.test(cookie)
    });

    // Probe auth status with same cookie
    try {
      const statusRes = await fetch(`${API_URL}/auth/status`, {
        headers: { cookie, accept: 'application/json' }
      });
      const statusText = await statusRes.text();
      console.info('Auth status probe', {
        endpoint: `${API_URL}/auth/status`,
        status: statusRes.status,
        body: statusText
      });
    } catch (probeErr: unknown) {
      console.error('Auth status probe failed', {
        endpoint: `${API_URL}/auth/status`,
        error: (probeErr as any)?.message || String(probeErr)
      });
    }

    const res = await fetch(endpoint, {
      // Explicitly forward the browser's cookies to the API (cross-origin SSR fetch)
      headers: {
        cookie,
        accept: 'application/json'
      }
    });
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
