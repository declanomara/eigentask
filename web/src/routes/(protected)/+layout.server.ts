import { redirect } from "@sveltejs/kit";
import type { LayoutServerLoad } from "./$types";
import { createApiClientForRequest } from "$lib/apiClient.server";

export const load: LayoutServerLoad = async ({ url, request }) => {
  const api = createApiClientForRequest();
  const cookie = request.headers.get("cookie") ?? "";

  let res;
  try {
    res = await api.authStatus(cookie);
  } catch (err) {
    const cause = err instanceof Error ? err.cause ?? err.message : String(err);
    console.error("[protected layout] API authStatus fetch failed:", cause);
    // Redirect to login so we don't 500; API unreachable usually means dev API isn't up
    throw redirect(
      307,
      `${api.externalBaseUrl}/auth/login?return_to=${encodeURIComponent(url.href)}&error=api_unreachable`,
    );
  }

  if (!res.ok) {
    throw redirect(
      307,
      `${api.externalBaseUrl}/auth/login?return_to=${encodeURIComponent(url.href)}`,
    );
  }
  if (!res.auth?.authenticated) {
    throw redirect(
      307,
      `${api.externalBaseUrl}/auth/login?return_to=${encodeURIComponent(url.href)}`,
    );
  }
  return { auth: res.auth };
};
