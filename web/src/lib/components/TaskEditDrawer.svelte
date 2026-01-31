<script lang="ts">
  import { env as publicEnv } from "$env/dynamic/public";
  import { createApiClient, type Task } from "$lib/apiClient";
  import OverlayShell from "$lib/components/ui/OverlayShell.svelte";
  import { createEventDispatcher } from "svelte";

  export let open = false;
  export let task: Task | null = null;

  const api = createApiClient({
    internalBaseUrl: publicEnv.PUBLIC_API_ORIGIN ?? "",
    externalBaseUrl: publicEnv.PUBLIC_API_ORIGIN ?? "",
  });

  const dispatch = createEventDispatcher<{
    close: void;
    saved: { task: Task };
    deleted: { id: number };
  }>();

  let title = "";
  let description = "";
  let plannedDuration: number | null = 60;
  let dueDate: string | null = null; // YYYY-MM-DD
  let error: string | null = null;
  let loading = false;
  let confirmingDelete = false;
  let lastTaskId: number | null = null;

  $: if (task && task.id !== lastTaskId) {
    title = task.title;
    description = task.description ?? "";
    plannedDuration = task.planned_duration ?? 60;
    dueDate = task.due_at ? task.due_at.slice(0, 10) : null;
    lastTaskId = task.id;
    confirmingDelete = false;
    error = null;
  } else if (!task) {
    title = "";
    description = "";
    plannedDuration = 60;
    dueDate = null;
    lastTaskId = null;
    confirmingDelete = false;
    error = null;
  }

  function close() {
    dispatch("close");
  }

  function normalizeDuration(value: number | null) {
    if (value === null || Number.isNaN(value)) return null;
    return value;
  }

  async function save() {
    if (!task) return;
    const trimmedTitle = title.trim();
    const durationValue = normalizeDuration(plannedDuration);

    if (!trimmedTitle) {
      error = "Title is required.";
      return;
    }
    if (durationValue !== null && durationValue < 15) {
      error = "Estimated minutes must be at least 15.";
      return;
    }

    loading = true;
    error = null;
    confirmingDelete = false;

    const normalizedDueDate = dueDate && dueDate.trim() ? dueDate : null;
    const due_at = normalizedDueDate ? new Date(normalizedDueDate).toISOString() : null;
    const res = await api.updateTask(task.id, {
      title: trimmedTitle,
      description: description.trim() || null,
      planned_duration: durationValue,
      due_at,
    });

    loading = false;

    if (!res.ok || !res.task) {
      error = res.error ?? "Unable to save changes.";
      return;
    }

    dispatch("saved", { task: res.task });
    dispatch("close");
  }

  async function deleteTask() {
    if (!task) return;
    if (!confirmingDelete) {
      confirmingDelete = true;
      return;
    }

    loading = true;
    error = null;

    const res = await api.deleteTask(task.id);
    loading = false;

    if (!res.ok) {
      error = res.error ?? "Unable to delete task.";
      confirmingDelete = false;
      return;
    }

    dispatch("deleted", { id: task.id });
    dispatch("close");
  }
</script>

<OverlayShell
  open={open && !!task}
  title="Edit Task"
  align="right"
  widthClass="max-w-md md:max-w-lg"
  on:close={close}
>
  <svelte:fragment slot="header" let:close>
    <div class="flex items-center justify-between px-4 py-3 border-b border-border-muted">
      <div>
        <p class="text-xs uppercase text-gray-500 tracking-wide">Task</p>
        <h3 class="text-lg font-semibold text-gray-800">{title || "Edit task"}</h3>
      </div>
      <button
        aria-label="Close"
        class="text-gray-500 hover:text-gray-700"
        on:click={close}
        type="button"
      >
        ✕
      </button>
    </div>
  </svelte:fragment>

  <form class="space-y-4" on:submit|preventDefault={save}>
    <label class="flex flex-col gap-2 text-sm text-gray-800">
      Title
      <input
        name="title"
        class="border rounded px-3 py-2 text-sm"
        bind:value={title}
        required
        placeholder="e.g. Draft project brief"
      />
    </label>

    <label class="flex flex-col gap-2 text-sm text-gray-800">
      Description
      <textarea
        name="description"
        class="border rounded px-3 py-2 text-sm"
        rows="3"
        bind:value={description}
        placeholder="What needs to be done?"
      ></textarea>
    </label>

    <label class="flex flex-col gap-2 text-sm text-gray-800">
      Estimated minutes
      <input
        name="planned_duration"
        type="number"
        min="15"
        step="15"
        class="border rounded px-3 py-2 text-sm"
        bind:value={plannedDuration}
      />
    </label>

    <label class="flex flex-col gap-2 text-sm text-gray-800">
      Due date (optional)
      <input
        name="due_at"
        type="date"
        class="border rounded px-3 py-2 text-sm"
        bind:value={dueDate}
      />
    </label>

    {#if error}
      <div class="text-sm text-rose-600 bg-rose-50 border border-rose-100 rounded px-3 py-2">
        {error}
      </div>
    {/if}

    <div class="flex items-center justify-between gap-3 pt-2">
      <div class="flex gap-2">
        <button
          type="submit"
          class="px-4 py-2 bg-blue-600 text-white rounded disabled:opacity-60"
          disabled={loading}
        >
          {loading ? "Saving..." : "Save changes"}
        </button>
        <button
          type="button"
          class="px-4 py-2 text-gray-700 border border-border rounded hover:bg-surface-hover"
          on:click={close}
          disabled={loading}
        >
          Cancel
        </button>
      </div>

      <button
        type="button"
        class={`px-4 py-2 rounded border ${confirmingDelete ? "bg-rose-600 text-white border-rose-600" : "border-rose-300 text-rose-700 hover:bg-rose-50"}`}
        on:click={deleteTask}
        disabled={loading}
      >
        {confirmingDelete ? "Confirm delete" : "Delete"}
      </button>
    </div>

    <p class="text-xs text-gray-500">
      Editing only changes task details. Scheduling and status stay as-is.
    </p>
  </form>
</OverlayShell>
