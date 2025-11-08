import { redirect } from "@sveltejs/kit";
import type { LayoutServerLoad } from "./$types";
import { env } from "$env/dynamic/private";
import { createApiClient } from "$lib/apiClient";

const API_URL_INTERNAL = (env.API_ORIGIN ?? "api_origin").replace(/\/+$/, "");

const API_URL_EXTERNAL = (env.PUBLIC_API_ORIGIN ?? "public_api_origin").replace(
  /\/+$/,
  "",
);

const api = createApiClient({
  internalBaseUrl: API_URL_INTERNAL,
  externalBaseUrl: API_URL_EXTERNAL,
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
