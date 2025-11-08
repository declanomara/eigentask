import { redirect } from "@sveltejs/kit";
import type { LayoutServerLoad } from "./$types";
import { env } from "$env/dynamic/private";

const API_URL_INTERNAL = (env.API_ORIGIN ?? "http://localhost:8000").replace(
  /\/+$/,
  "",
);

const API_URL_EXTERNAL = (
  env.PUBLIC_API_ORIGIN ?? "http://localhost:8000"
).replace(/\/+$/, "");

export const load: LayoutServerLoad = async ({ fetch, url, request }) => {
  const cookie = request.headers.get("cookie") ?? "";
  const res = await fetch(`${API_URL_INTERNAL}/auth/status`, {
    // Forward cookies explicitly for cross-origin SSR
    headers: {
      cookie,
      accept: "application/json",
      connection: "close",
    },
  });
  if (!res.ok) {
    throw redirect(
      307,
      `${API_URL_EXTERNAL}/auth/login?return_to=${encodeURIComponent(url.href)}`,
    );
  }
  const data = await res.json();
  if (!data?.authenticated) {
    throw redirect(
      307,
      `${API_URL_EXTERNAL}/auth/login?return_to=${encodeURIComponent(url.href)}`,
    );
  }
  return { authenticated: true, user: data.user ?? null };
};
