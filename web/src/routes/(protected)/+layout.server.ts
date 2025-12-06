import { redirect } from "@sveltejs/kit";
import type { LayoutServerLoad } from "./$types";
import { createApiClientForRequest } from "$lib/apiClient.server";

export const load: LayoutServerLoad = async ({ url, request }) => {
  const api = createApiClientForRequest();
  const cookie = request.headers.get("cookie") ?? "";

  const res = await api.authStatus(cookie);

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
