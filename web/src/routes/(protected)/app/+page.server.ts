import type { Actions, PageServerLoad } from "./$types";
import { redirect } from "@sveltejs/kit";
import { env as privateEnv } from "$env/dynamic/private";
import { env as publicEnv } from "$env/dynamic/public";
import { createApiClient, type AuthStatus } from "$lib/apiClient";

const api = createApiClient({
  internalBaseUrl: privateEnv.API_ORIGIN ?? "API_ORIGIN NOT SET",
  externalBaseUrl: publicEnv.PUBLIC_API_ORIGIN ?? "PUBLIC_API_ORIGIN NOT SET",
});

export const load: PageServerLoad = async (event) => {
  // Pull auth data from layout
  const parent = await event.parent();
  const auth = (parent?.auth ?? undefined) as AuthStatus | undefined;

  const cookie = event.request.headers.get("cookie") ?? "";
  const res = await api.getTasks(cookie);

  // If the internal API call failed, surface an error (no automatic redirect here)
  if (!res.ok) {
    return { tasks: [], error: res.error ?? `API error` } as any;
  }

  const tasks = res.tasks;
  return { tasks, auth, error: res.ok ? null : res.error };
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

    const input = description ? { title, description } : { title };
    const res = await api.createTask(input, cookie);
    if (!res.ok) {
      return { success: false, error: res.error ?? "Create failed" };
    }

    // PRG: redirect after successful creation
    throw redirect(303, "/app");
  },
  delete: async ({ request, fetch }) => {
    const cookie = request.headers.get("cookie") ?? "";
    const form = await request.formData();
    const idRaw = form.get("id");
    const id = Number(idRaw);
    if (!id || Number.isNaN(id)) {
      return { success: false, error: "Invalid id" };
    }

    const res = await api.deleteTask(id, cookie);
    if (!res.ok) {
      return { success: false, error: res.error ?? "Delete failed" };
    }

    // PRG: redirect after successful deletion
    throw redirect(303, "/app");
  },
  edit: async ({ request, fetch }) => {
    const cookie = request.headers.get("cookie") ?? "";
    const form = await request.formData();
    const id = Number(form.get("id") ?? "");
    const title = String(form.get("title") ?? "").trim() || undefined;
    const description = String(form.get("description") ?? "") || undefined;
    if (!id) {
      return { success: false, error: "Invalid id" };
    }
    if (!title && !description) {
      return { success: false, error: "Title or description is required" };
    }

    // Use apiClient to update
    const res = await api.updateTask(id, { title, description }, cookie);
    if (!res.ok) {
      return { success: false, error: res.error ?? "Update failed" };
    }
    // PRG: redirect after success
    throw redirect(303, "/app");
  },
};
