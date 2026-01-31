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

  $: statusKey = (task.status ?? "BACKLOG") as TaskStatus;
  $: canComplete =
    showCompleteButton && statusKey !== "COMPLETED" && statusKey !== "REMOVED";
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
      {#if canComplete}
        <button
          class="w-7 h-7 inline-flex items-center justify-center rounded-full border border-green-200 text-green-700 bg-green-50 hover:bg-green-100 hover:border-green-300"
          aria-label="Mark completed"
          title="Mark completed"
          on:click={completeTask}
        >
          ✓
        </button>
      {/if}
      {#if statusKey === "COMPLETED"}
        <button
          class={`text-[11px] px-2 py-1 rounded-full border ${statusTone[statusKey]} hover:opacity-80`}
          aria-label="Mark not completed"
          title="Mark not completed"
          on:click={reopenTask}
        >
          {statusCopy[statusKey]}
        </button>
      {:else}
        <span class={`text-[11px] px-2 py-1 rounded-full border ${statusTone[statusKey]}`}>
          {statusCopy[statusKey]}
        </span>
      {/if}
    </div>
  </div>

  {#if task.description}
    <p class="text-sm text-gray-600 line-clamp-2">{task.description}</p>
  {/if}

  <div class="text-xs text-gray-500 flex flex-wrap gap-3">
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
