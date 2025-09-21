import type { PageServerLoad } from './$types';
import { env } from '$env/dynamic/private';

const API_URL = env.API_ORIGIN ?? 'http://localhost:8000';

export const load: PageServerLoad = async ({ fetch, request }) => {
  const cookie = request.headers.get('cookie') ?? '';
  const host = request.headers.get('host') ?? '';

  const probe = async (fullUrl: string) => {
    const out: Record<string, unknown> = {
      requested: fullUrl,
      api_origin: API_URL,
      host
    };
    try {
      let res = await fetch(fullUrl, { headers: { cookie, accept: 'application/json' } });
      if ([301, 302, 303, 307, 308].includes(res.status)) {
        const loc = res.headers.get('location');
        out.redirected = true;
        out.location = loc;
        if (loc) {
          const absolute = loc.startsWith('http') ? loc : new URL(loc, API_URL).toString();
          res = await fetch(absolute, { headers: { cookie, accept: 'application/json' } });
        }
      }
      out.status = res.status;
      out.statusText = res.statusText;
      out.final_url = res.url;
      out.headers = Array.from(res.headers.entries());
      try {
        const text = await res.clone().text();
        out.bodyText = text;
        try {
          out.bodyJson = JSON.parse(text);
        } catch {}
      } catch (e) {
        out.readError = (e as any)?.message || String(e);
      }
    } catch (e) {
      out.error = (e as any)?.message || String(e);
      out.stack = (e as any)?.stack;
    }
    return out;
  };

  return {
    diagnostics: {
      page: '/app',
      host,
      api_origin: API_URL,
      cookie_present: cookie.length > 0,
      cookie_length: cookie.length,
      cookie_has_sid: /(^|;\s*)sid=/.test(cookie)
    },
    probe_details: {
      auth_status: await probe(`${API_URL}/auth/status`),
      tasks: await probe(`${API_URL}/tasks/`)
    }
  } satisfies Record<string, unknown>;
};
