<script lang="ts">
  import { env as publicEnv } from "$env/dynamic/public";
  import { createApiClient, type Task, type Session } from "$lib/apiClient";
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
    sessionsChanged: { taskId: number };
  }>();

  let title = "";
  let description = "";
  let plannedDuration: number | string | null = 60;
  let dueDate: string | null = null; // YYYY-MM-DD
  let error: string | null = null;
  let loading = false;
  let confirmingDelete = false;
  let lastTaskId: number | null = null;
  let taskSessions: Session[] = [];
  let sessionsLoading = false;
  let addSessionOpen = false;
  let addSessionStart = "";
  let addSessionDuration: number | string = 60;
  let addSessionError: string | null = null;

  const pad2 = (value: number) => value.toString().padStart(2, "0");

  function toLocalInputValue(date: Date) {
    return `${date.getFullYear()}-${pad2(date.getMonth() + 1)}-${pad2(date.getDate())}T${pad2(
      date.getHours(),
    )}:${pad2(date.getMinutes())}`;
  }

  function roundToNearestInterval(date: Date, minutes: number) {
    const rounded = new Date(date);
    const remainder = rounded.getMinutes() % minutes;
    const delta = remainder >= minutes / 2 ? minutes - remainder : -remainder;
    rounded.setMinutes(rounded.getMinutes() + delta, 0, 0);
    return rounded;
  }

  function handleSessionStartBlur() {
    if (!addSessionStart) return;
    const parsed = new Date(addSessionStart);
    if (Number.isNaN(parsed.getTime())) return;
    const rounded = roundToNearestInterval(parsed, 15);
    addSessionStart = toLocalInputValue(rounded);
  }

  function roundDuration(value: number) {
    return Math.round(value / 15) * 15;
  }

  function handleDurationBlur() {
    const raw = typeof addSessionDuration === "string" ? Number(addSessionDuration) : addSessionDuration;
    if (!raw || Number.isNaN(raw)) return;
    addSessionDuration = roundDuration(raw);
  }

  $: if (task && task.id !== lastTaskId) {
    title = task.title;
    description = task.description ?? "";
    plannedDuration = task.planned_duration ?? 60;
    dueDate = task.due_at ? task.due_at.slice(0, 10) : null;
    lastTaskId = task.id;
    confirmingDelete = false;
    error = null;
    addSessionOpen = false;
    addSessionStart = "";
    addSessionDuration = 60;
    addSessionError = null;
    taskSessions = [];
    void loadSessions();
  } else if (!task) {
    title = "";
    description = "";
    plannedDuration = 60;
    dueDate = null;
    lastTaskId = null;
    confirmingDelete = false;
    error = null;
    taskSessions = [];
    addSessionOpen = false;
    addSessionStart = "";
    addSessionDuration = 60;
    addSessionError = null;
  }

  async function loadSessions() {
    if (!task) return;
    sessionsLoading = true;
    const res = await api.getSessionsForTask(task.id);
    taskSessions = res.ok && res.sessions ? res.sessions : [];
    sessionsLoading = false;
  }

  function formatSessionTime(s: Session) {
    const start = new Date(s.scheduled_start_at);
    const end = new Date(s.scheduled_end_at);
    return `${start.toLocaleString(undefined, { dateStyle: "short", timeStyle: "short" })} – ${end.toLocaleTimeString(undefined, { timeStyle: "short" })}`;
  }

  async function completeSession(s: Session) {
    if (!task || s.status === "COMPLETED") return;
    const res = await api.updateSession(task.id, s.id, { status: "COMPLETED" });
    if (res.ok) {
      await loadSessions();
      dispatch("sessionsChanged", { taskId: task.id });
    }
  }

  async function deleteSession(s: Session) {
    if (!task) return;
    const res = await api.deleteSession(task.id, s.id);
    if (res.ok) {
      await loadSessions();
      dispatch("sessionsChanged", { taskId: task.id });
    }
  }

  async function addSession() {
    if (!task) return;
    const start = addSessionStart ? new Date(addSessionStart) : null;
    const rawDuration =
      typeof addSessionDuration === "string" ? parseInt(addSessionDuration, 10) : addSessionDuration;
    if (!start || Number.isNaN(start.getTime())) {
      addSessionError = "Pick a date and time.";
      return;
    }
    if (!rawDuration || rawDuration <= 0) {
      addSessionError = "Duration must be greater than 0 minutes.";
      return;
    }
    const duration = roundDuration(rawDuration);
    if (duration <= 0) {
      addSessionError = "Duration must be greater than 0 minutes.";
      return;
    }
    const end = new Date(start.getTime() + duration * 60000);
    addSessionError = null;
    const res = await api.createSession(task.id, {
      scheduled_start_at: start.toISOString(),
      scheduled_end_at: end.toISOString(),
    });
    if (!res.ok) {
      addSessionError = res.error ?? "Failed to add session.";
      return;
    }
    addSessionOpen = false;
    addSessionStart = "";
    addSessionDuration = 60;
    await loadSessions();
    dispatch("sessionsChanged", { taskId: task.id });
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
    class="flex flex-col min-h-0 flex-1"
    on:submit|preventDefault={save}
    aria-describedby={error ? "edit-error" : undefined}
  >
    <div class="flex-1 min-h-0 flex flex-col space-y-4">
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

      <div class="flex flex-col gap-2 pt-2 border-t border-border-muted min-h-0 flex-1">
        <div class="flex items-center justify-between">
          <Label>Sessions</Label>
          {#if !addSessionOpen}
            <Button
              type="button"
              variant="secondary"
              disabled={loading || sessionsLoading}
              on:click={() => (addSessionOpen = true)}
            >
              Add session
            </Button>
          {/if}
        </div>
        {#if addSessionOpen}
          <div class="rounded-lg border border-border bg-surface-hover/50 p-3 space-y-2">
            <input
              type="datetime-local"
              bind:value={addSessionStart}
              on:blur={handleSessionStartBlur}
              class="w-full rounded border border-border px-2 py-1.5 text-sm"
            />
            <div class="flex items-center gap-2">
              <Label forId="add-session-duration">Duration</Label>
              <Input
                id="add-session-duration"
                type="number"
                min={1}
                step={15}
                bind:value={addSessionDuration}
                on:blur={handleDurationBlur}
              />
            </div>
            {#if addSessionError}
              <p class="text-sm text-rose-600">{addSessionError}</p>
            {/if}
            <div class="flex items-center gap-2">
              <Button type="button" variant="primary" on:click={addSession}>Add</Button>
              <Button type="button" variant="secondary" on:click={() => (addSessionOpen = false)}>
                Cancel
              </Button>
            </div>
          </div>
        {/if}
        <div class="min-h-0 flex-1 overflow-y-auto pr-1">
          {#if sessionsLoading}
            <p class="text-sm text-gray-500">Loading sessions…</p>
          {:else if taskSessions.length === 0}
            <p class="text-sm text-gray-500">No sessions. Add one or drag this task onto the timeline.</p>
          {:else}
            <ul class="space-y-2">
              {#each taskSessions as session (session.id)}
                <li class="flex items-center justify-between gap-2 rounded-lg border border-border bg-surface px-3 py-2 text-sm">
                  <span class="min-w-0 truncate">{formatSessionTime(session)}</span>
                  <span class="flex-shrink-0 text-xs {session.status === 'COMPLETED' ? 'text-gray-600' : 'text-blue-600'}">
                    {session.status === "COMPLETED" ? "Done" : "Scheduled"}
                  </span>
                  <div class="flex items-center gap-1 flex-shrink-0">
                    {#if session.status === "INCOMPLETE"}
                      <button
                        type="button"
                        class="text-xs p-1.5 rounded border border-green-200 bg-green-50 text-green-700 hover:bg-green-100 inline-flex items-center justify-center"
                        aria-label="Complete session"
                        on:click={() => completeSession(session)}
                      >
                        <svg xmlns="http://www.w3.org/2000/svg" class="h-3.5 w-3.5" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">
                          <path d="M4 15s1-1 4-1 5 2 8 2 4-1 4-1V3s-1 1-4 1-5-2-8-2-4 1-4 1z" />
                          <line x1="4" y1="22" x2="4" y2="15" />
                        </svg>
                      </button>
                    {/if}
                    <button
                      type="button"
                      class="text-xs p-1.5 rounded border border-rose-200 text-rose-700 hover:bg-rose-50 inline-flex items-center justify-center"
                      aria-label="Delete session"
                      on:click={() => deleteSession(session)}
                    >
                      <svg xmlns="http://www.w3.org/2000/svg" class="h-3.5 w-3.5" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">
                        <path d="M3 6h18" />
                        <path d="M19 6v14c0 1-1 2-2 2H7c-1 0-2-1-2-2V6" />
                        <path d="M8 6V4c0-1 1-2 2-2h4c1 0 2 1 2 2v2" />
                        <line x1="10" y1="11" x2="10" y2="17" />
                        <line x1="14" y1="11" x2="14" y2="17" />
                      </svg>
                    </button>
                  </div>
                </li>
              {/each}
            </ul>
          {/if}
        </div>
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
