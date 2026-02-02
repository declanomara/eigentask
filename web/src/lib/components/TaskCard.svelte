<script lang="ts">
  import { createEventDispatcher } from "svelte";
  import type { Task, TaskStatus } from "$lib/apiClient";

  export let task: Task;
  export let showCompleteButton = false;
  export let draggable = true;

  const dispatch = createEventDispatcher<{
    select: { task: Task };
    complete: { task: Task };
    reopen: { task: Task };
    completeNextSession: { task: Task };
  }>();

  const statusCopy: Record<TaskStatus, string> = {
    BACKLOG: "Backlog",
    PLANNED: "Scheduled",
    COMPLETED: "Completed",
    REMOVED: "Removed",
  };

  const statusTone: Record<TaskStatus, string> = {
    BACKLOG: "bg-surface-hover text-gray-700 border-border",
    PLANNED: "bg-blue-50 text-blue-700 border-blue-200",
    COMPLETED: "bg-green-50 text-green-700 border-green-200",
    REMOVED: "bg-rose-50 text-rose-700 border-rose-200",
  };

  const toUtcDate = (value: string | null) => {
    if (!value) return null;
    // Treat date-only strings as UTC midnight; otherwise rely on provided timezone or Z.
    const normalized = value.includes("T") ? value : `${value}T00:00:00Z`;
    const d = new Date(normalized);
    return Number.isNaN(d.getTime()) ? null : d;
  };

  const dueFormatter = new Intl.DateTimeFormat(undefined, {
    month: "short",
    day: "numeric",
    timeZone: "UTC",
  });

  const formatDueDate = (value: string | null) => {
    const d = toUtcDate(value);
    if (!d) return null;
    return dueFormatter.format(d);
  };

  const formatTimeRange = (startRaw: string | null, endRaw: string | null) => {
    const start = toUtcDate(startRaw);
    const end = toUtcDate(endRaw);
    if (!start) return "";
    const startStr = start.toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" });
    if (!end) return startStr;
    const endStr = end.toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" });
    return `${startStr} - ${endStr}`;
  };

  function handleClick(event: MouseEvent | KeyboardEvent) {
    // Allow keyboard callers that intentionally call preventDefault()
    if (event instanceof MouseEvent && event.defaultPrevented) return;
    dispatch("select", { task });
  }

  function completeTask(event: MouseEvent) {
    event.stopPropagation();
    dispatch("complete", { task });
  }

  function completeNextSession(event: MouseEvent) {
    event.stopPropagation();
    dispatch("completeNextSession", { task });
  }

  function handleKeydown(event: KeyboardEvent) {
    if (event.key === "Enter" || event.key === " ") {
      event.preventDefault();
      handleClick(event);
    }
  }

  function reopenTask(event: MouseEvent) {
    event.stopPropagation();
    dispatch("reopen", { task });
  }

  $: pendingSessions = Math.max(
    0,
    (task.sessions_count ?? 0) - (task.completed_sessions_count ?? 0),
  );
  let effectiveStatus: TaskStatus = "BACKLOG";
  $: effectiveStatus =
    task.status === "COMPLETED"
      ? "COMPLETED"
      : task.status === "REMOVED"
        ? "REMOVED"
        : pendingSessions > 0
          ? "PLANNED"
          : "BACKLOG";
  $: statusKey = effectiveStatus;
  $: canComplete =
    showCompleteButton && statusKey !== "COMPLETED" && statusKey !== "REMOVED";
  $: sessionsTotal = task.sessions_count ?? 0;
  $: sessionsCompleted = task.completed_sessions_count ?? 0;
  $: hasIncompleteSessions = sessionsTotal > 0 && sessionsCompleted < sessionsTotal;
  $: canCompleteNextSession = showCompleteButton && hasIncompleteSessions && statusKey !== "COMPLETED";
  $: dueDate = toUtcDate(task.due_at);
  $: isOverdue = (() => {
    if (!dueDate || statusKey === "COMPLETED") return false;
    const endOfDayUtc = new Date(
      Date.UTC(
        dueDate.getUTCFullYear(),
        dueDate.getUTCMonth(),
        dueDate.getUTCDate(),
        23,
        59,
        59,
        999,
      ),
    );
    return endOfDayUtc.getTime() < Date.now();
  })();
  $: dueLabel = formatDueDate(task.due_at);
</script>

<div
  class={`rounded-xl border p-4 hover:shadow-md transition-shadow flex flex-col gap-2 select-none ${draggable ? "cursor-grab" : "cursor-pointer"} ${statusKey === "COMPLETED" ? "opacity-80" : ""} ${
    isOverdue ? "border-rose-200 bg-rose-50/70" : "border-border bg-surface"
  }`}
  draggable={draggable}
  data-dnd-id={task.id}
  on:click={handleClick}
  role="button"
  tabindex="0"
  on:keydown={handleKeydown}
>
  <div class="flex items-start justify-between gap-3">
    <h3 class="font-semibold text-gray-800 text-base leading-tight">
      {task.title}
    </h3>
    <div class="flex items-center gap-2">
      {#if canCompleteNextSession}
        <button
          class="p-1.5 rounded-full border border-amber-200 text-amber-800 bg-amber-50 hover:bg-amber-100 inline-flex items-center justify-center"
          aria-label="Complete next session"
          title="Complete next session"
          on:click={completeNextSession}
        >
          <svg xmlns="http://www.w3.org/2000/svg" class="h-3.5 w-3.5" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">
            <path d="M4 15s1-1 4-1 5 2 8 2 4-1 4-1V3s-1 1-4 1-5-2-8-2-4 1-4 1z" />
            <line x1="4" y1="22" x2="4" y2="15" />
          </svg>
        </button>
      {/if}
      {#if canComplete}
        <button
          class="w-7 h-7 inline-flex items-center justify-center rounded-full border border-green-200 text-green-700 bg-green-50 hover:bg-green-100 hover:border-green-300"
          aria-label="Mark task completed"
          title="Mark task completed"
          on:click={completeTask}
        >
          ✓
        </button>
      {/if}
      {#if statusKey === "COMPLETED"}
        <button
          class="text-[11px] px-2 py-1 rounded-full border border-gray-200 bg-gray-50 text-gray-700 hover:bg-gray-100 inline-flex items-center gap-1"
          aria-label="Reopen task"
          title="Reopen task"
          on:click={reopenTask}
        >
          <svg xmlns="http://www.w3.org/2000/svg" class="h-3.5 w-3.5 shrink-0" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">
            <path d="M3 12a9 9 0 1 0 9-9 9.75 9.75 0 0 0-6.74 2.74L3 8" />
            <path d="M3 3v5h5" />
          </svg>
          Reopen
        </button>
      {/if}
    </div>
  </div>

  {#if task.description}
    <p class="text-sm text-gray-600 line-clamp-2">{task.description}</p>
  {/if}

  <div class="text-xs text-gray-500 flex flex-wrap gap-3 items-center">
    <span
      class="flex items-center gap-1.5 font-medium"
      aria-label="Status: {statusCopy[statusKey]}"
    >
      <span
        class="w-1.5 h-1.5 shrink-0 rounded-full {statusKey === 'PLANNED' ? 'bg-blue-500' : statusKey === 'REMOVED' ? 'bg-rose-400' : statusKey === 'COMPLETED' ? 'bg-green-500' : 'bg-gray-400'}"
      ></span>
      {statusCopy[statusKey]}
    </span>
    {#if sessionsTotal > 0}
      <span class="font-medium">Sessions: {sessionsCompleted}/{sessionsTotal}</span>
    {/if}
    {#if task.planned_duration}
      <span class="font-medium">{task.planned_duration} min</span>
    {/if}
    {#if task.planned_start_at}
      <span>{formatTimeRange(task.planned_start_at, task.planned_end_at)}</span>
    {/if}
    {#if dueLabel}
      <span
        class={`ml-auto italic text-[11px] leading-tight self-center ${isOverdue ? "text-rose-600 font-semibold" : "text-gray-600"}`}
      >
        Due {dueLabel}
      </span>
    {/if}
  </div>
</div>
