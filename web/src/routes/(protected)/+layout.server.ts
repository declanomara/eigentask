import { redirect } from "@sveltejs/kit";
import type { LayoutServerLoad } from "./$types";
import { env as privateEnv } from "$env/dynamic/private";
import { env as publicEnv } from "$env/dynamic/public";
import { createApiClient } from "$lib/apiClient";

const api = createApiClient({
  internalBaseUrl: privateEnv.API_ORIGIN ?? "API_ORIGIN NOT SET",
  externalBaseUrl: publicEnv.PUBLIC_BASE_URL ?? "PUBLIC_BASE_URL NOT SET",
});

export const load: LayoutServerLoad = async ({ url, request }) => {
  const cookie = request.headers.get("cookie") ?? "";

  const res = await api.authStatus(cookie);

  if (!res.ok) {
    throw redirect(
      307,
      `${API_URL_EXTERNAL}/auth/login?return_to=${encodeURIComponent(url.href)}`,
    );
  }
  if (!res.auth?.authenticated) {
    throw redirect(
      307,
      `${API_URL_EXTERNAL}/auth/login?return_to=${encodeURIComponent(url.href)}`,
    );
  }
  return { auth: res.auth };
};
