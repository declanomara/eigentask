<script lang="ts">
  import { env as publicEnv } from "$env/dynamic/public";
  import { createApiClient, type Task } from "$lib/apiClient";
  import Button from "$lib/components/ui/Button.svelte";
  import Input from "$lib/components/ui/Input.svelte";
  import Label from "$lib/components/ui/Label.svelte";
  import OverlayShell from "$lib/components/ui/OverlayShell.svelte";
  import Textarea from "$lib/components/ui/Textarea.svelte";
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
  let plannedDuration: number | string | null = 60;
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

  function normalizeDuration(value: number | string | null): number | null {
    if (value === null || value === "") return null;
    const n = typeof value === "string" ? Number(value) : value;
    if (Number.isNaN(n)) return null;
    return n;
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
    <div class="flex items-center justify-between px-4 py-3 border-b border-border-muted flex-shrink-0">
      <div>
        <p class="text-xs uppercase text-gray-500 tracking-wide">Task</p>
        <h3 class="text-lg font-semibold text-gray-800">{title || "Edit task"}</h3>
      </div>
      <button
        aria-label="Close"
        class="text-gray-500 hover:text-gray-700 focus:outline-none focus:ring-2 focus:ring-blue-500/30 rounded"
        on:click={close}
        type="button"
      >
        ✕
      </button>
    </div>
  </svelte:fragment>

  <form
    class="flex flex-col min-h-full"
    on:submit|preventDefault={save}
    aria-describedby={error ? "edit-error" : undefined}
  >
    <div class="flex-1 space-y-4">
      <div class="flex flex-col gap-1.5">
        <Label forId="edit-title">Title</Label>
        <Input
          id="edit-title"
          type="text"
          name="title"
          bind:value={title}
          required
          placeholder="e.g. Draft project brief"
        />
      </div>

      <div class="flex flex-col gap-1.5">
        <Label forId="edit-description">Description</Label>
        <Textarea
          id="edit-description"
          name="description"
          bind:value={description}
          placeholder="What needs to be done?"
          rows={3}
        />
      </div>

      <div class="flex flex-col gap-1.5">
        <Label forId="edit-duration">Estimated minutes</Label>
        <Input
          id="edit-duration"
          type="number"
          name="planned_duration"
          bind:value={plannedDuration}
          min={15}
          step={15}
        />
      </div>

      <div class="flex flex-col gap-1.5">
        <Label forId="edit-due">Due date (optional)</Label>
        <Input
          id="edit-due"
          type="date"
          name="due_at"
          bind:value={dueDate}
        />
      </div>

      {#if error}
        <div
          id="edit-error"
          class="text-sm text-rose-600 bg-rose-50 border border-rose-100 rounded-lg px-3 py-2"
          role="alert"
        >
          {error}
        </div>
      {/if}
    </div>

    <div class="mt-auto pt-4 border-t border-border-muted space-y-3">
      <div class="flex items-center justify-between gap-3">
        <div class="flex gap-2">
          <Button type="submit" variant="primary" disabled={loading}>
            {loading ? "Saving…" : "Save changes"}
          </Button>
          <Button type="button" variant="secondary" disabled={loading} on:click={close}>
            Cancel
          </Button>
        </div>
        <Button
          type="button"
          variant="danger"
          confirming={confirmingDelete}
          disabled={loading}
          on:click={deleteTask}
        >
          {confirmingDelete ? "Confirm delete" : "Delete"}
        </Button>
      </div>
      <p class="text-xs text-gray-500">
        Editing only changes task details. Scheduling and status stay as-is.
      </p>
    </div>
  </form>
</OverlayShell>
