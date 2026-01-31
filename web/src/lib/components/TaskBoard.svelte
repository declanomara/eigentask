<script lang="ts">
    import { createEventDispatcher } from "svelte";
    import type { Task } from "$lib/apiClient";
    import type { DndEvent, DndZoneOptions } from "svelte-dnd-action";
    import TaskColumn from "./TaskColumn.svelte";
    import TaskCard from "./TaskCard.svelte";

    export let backlogTasks: Task[] = [];
    export let scheduledTasks: Task[] = [];
    export let completedTasks: Task[] = [];

    const dispatch = createEventDispatcher<{
        consider: DndEvent<Task>;
        finalize: DndEvent<Task>;
        select: { task: Task };
        complete: { task: Task };
        reopen: { task: Task };
    }>();

    $: backlogOptions = { id: "backlog", items: backlogTasks } satisfies DndZoneOptions<Task>;
    $: scheduledOptions = { id: "scheduled", items: scheduledTasks } satisfies DndZoneOptions<Task>;

    function forward(event: CustomEvent<DndEvent<Task>>) {
        dispatch(event.type as "consider" | "finalize", event.detail);
    }

    function forwardSelect(event: CustomEvent<{ task: Task }>) {
        dispatch("select", event.detail);
    }

    function forwardComplete(event: CustomEvent<{ task: Task }>) {
        dispatch("complete", event.detail);
    }

    function forwardReopen(event: CustomEvent<{ task: Task }>) {
        dispatch("reopen", event.detail);
    }

    let showCompleted = false;
</script>

<div class="grid grid-cols-1 md:grid-cols-2 gap-4 p-2 w-full">
    <TaskColumn
        title="Backlog"
        tasks={backlogTasks}
        zoneOptions={backlogOptions}
        on:consider={forward}
        on:finalize={forward}
        on:select={forwardSelect}
        on:complete={forwardComplete}
    />
    <TaskColumn
        title="Scheduled"
        tasks={scheduledTasks}
        zoneOptions={scheduledOptions}
        on:consider={forward}
        on:finalize={forward}
        on:select={forwardSelect}
        on:complete={forwardComplete}
    />
</div>

<div class="px-2 mt-3 w-full">
    <details class="rounded-xl border border-border bg-surface" bind:open={showCompleted}>
        <summary
            class="w-full flex items-center justify-between px-4 py-2 text-sm text-gray-700 hover:bg-surface-hover transition cursor-pointer select-none list-none"
        >
            <div class="flex items-center gap-2">
                <span class="text-gray-600">{showCompleted ? "▾" : "▸"}</span>
                <span class="font-semibold">Completed</span>
                <span class="text-xs text-gray-500 bg-surface-hover px-2 py-0.5 rounded-full"
                    >{completedTasks.length}</span
                >
            </div>
            <span class="text-xs text-gray-500">{showCompleted ? "Hide" : "Show"}</span>
        </summary>

        <div class="mt-1 mb-2 px-2 flex flex-col gap-2">
            {#if completedTasks.length > 0}
                {#each completedTasks as task (task.id)}
                    <TaskCard task={task} draggable={false} on:reopen={forwardReopen} />
                {/each}
            {:else}
                <div class="text-sm text-gray-400 italic px-1">No completed tasks yet.</div>
            {/if}
        </div>
    </details>
</div>
