import type { Actions, PageServerLoad } from "./$types";
import { redirect } from "@sveltejs/kit";
import { env } from "$env/dynamic/private";

const API_URL_INTERNAL = (env.API_ORIGIN ?? "http://localhost:8000").replace(
  /\/+$/,
  "",
);

const API_URL_EXTERNAL = (
  env.PUBLIC_API_ORIGIN ?? "http://localhost:8000"
).replace(/\/+$/, "");

export const load: PageServerLoad = async ({ fetch, request }) => {
  const cookie = request.headers.get("cookie") ?? "";
  try {
    let res = await fetch(`${API_URL_INTERNAL}/tasks/`, {
      headers: { cookie, accept: "application/json", connection: "close" },
    });
    // Manually follow one redirect to preserve headers if any
    if ([301, 302, 303, 307, 308].includes(res.status)) {
      const loc = res.headers.get("location");
      if (loc) {
        const absolute = loc.startsWith("http")
          ? loc
          : new URL(loc, API_URL_INTERNAL).toString();
        res = await fetch(absolute, {
          headers: { cookie, accept: "application/json", connection: "close" },
        });
      }
    }
    if (!res.ok) {
      return {
        tasks: [],
        error: `API responded ${res.status} ${res.statusText}`,
      } as any;
    }
    const tasks = await res.json();
    return { tasks };
  } catch (e: any) {
    return { tasks: [], error: e?.message || String(e) } as any;
  }
};

export const actions: Actions = {
  create: async ({ request, fetch }) => {
    const cookie = request.headers.get("cookie") ?? "";
    const form = await request.formData();
    const title = String(form.get("title") ?? "").trim();
    const description = String(form.get("description") ?? "") || null;
    if (!title) {
      return { success: false, error: "Title is required" };
    }
    try {
      const res = await fetch(`${API_URL_INTERNAL}/tasks/`, {
        method: "POST",
        headers: {
          cookie,
          "content-type": "application/json",
          accept: "application/json",
          connection: "close",
        },
        body: JSON.stringify({ title, description }),
      });
      if (!res.ok) {
        return {
          success: false,
          error: `Create failed: ${res.status} ${res.statusText}`,
        };
      }
      // PRG pattern to avoid resubmission on refresh
      throw redirect(303, "/app");
    } catch (e: any) {
      return { success: false, error: e?.message || String(e) };
    }
  },
  delete: async ({ request, fetch }) => {
    const cookie = request.headers.get("cookie") ?? "";
    const form = await request.formData();
    const idRaw = form.get("id");
    const id = Number(idRaw);
    if (!id || Number.isNaN(id)) {
      return { success: false, error: "Invalid id" };
    }
    try {
      const res = await fetch(`${API_URL_INTERNAL}/tasks/${id}`, {
        method: "DELETE",
        headers: {
          cookie,
          accept: "application/json",
          connection: "close",
        },
      });
      if (!res.ok && res.status !== 204) {
        return {
          success: false,
          error: `Delete failed: ${res.status} ${res.statusText}`,
        };
      }
      // PRG pattern
      throw redirect(303, "/app");
    } catch (e: any) {
      return { success: false, error: e?.message || String(e) };
    }
  },
};
