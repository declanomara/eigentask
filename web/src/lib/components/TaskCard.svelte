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
    BACKLOG: "bg-gray-100 text-gray-700 border-gray-200",
    PLANNED: "bg-blue-50 text-blue-700 border-blue-200",
    COMPLETED: "bg-green-50 text-green-700 border-green-200",
    REMOVED: "bg-rose-50 text-rose-700 border-rose-200",
  };

  const toDate = (value: string | null) => (value ? new Date(value) : null);

  const formatTimeRange = (startRaw: string | null, endRaw: string | null) => {
    const start = toDate(startRaw);
    const end = toDate(endRaw);
    if (!start) return "";
    const startStr = start.toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" });
    if (!end) return startStr;
    const endStr = end.toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" });
    return `${startStr} - ${endStr}`;
  };

  function handleClick(event: MouseEvent) {
    if (event.defaultPrevented) return;
    dispatch("select", { task });
  }

  function completeTask(event: MouseEvent) {
    event.stopPropagation();
    dispatch("complete", { task });
  }

  function reopenTask(event: MouseEvent) {
    event.stopPropagation();
    dispatch("reopen", { task });
  }

  $: statusKey = (task.status ?? "BACKLOG") as TaskStatus;
  $: canComplete =
    showCompleteButton && statusKey !== "COMPLETED" && statusKey !== "REMOVED";
</script>

<div
  class={`bg-white rounded-xl border border-gray-200 p-4 hover:shadow-md transition-shadow flex flex-col gap-2 select-none ${draggable ? "cursor-grab" : "cursor-pointer"} ${statusKey === "COMPLETED" ? "opacity-80" : ""}`}
  draggable={draggable}
  data-dnd-id={task.id}
  on:click={handleClick}
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
  </div>
</div>
