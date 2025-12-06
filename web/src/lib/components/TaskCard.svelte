<script lang="ts">
    import type { Task, TaskStatus } from "$lib/apiClient";

    export let task: Task;

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

    $: statusKey = (task.status ?? "BACKLOG") as TaskStatus;
</script>

<div
    class="bg-white rounded-xl border border-gray-200 p-4 hover:shadow-md transition-shadow cursor-grab flex flex-col gap-2 select-none"
    draggable="true"
    data-dnd-id={task.id}
>
    <div class="flex items-start justify-between gap-3">
        <h3 class="font-semibold text-gray-800 text-base leading-tight">
            {task.title}
        </h3>
        <span class={`text-[11px] px-2 py-1 rounded-full border ${statusTone[statusKey]}`}>
            {statusCopy[statusKey]}
        </span>
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
