<script lang="ts">
    import { createEventDispatcher } from "svelte";
    import { dndzone, type DndEvent, type DndItem, type DndZoneOptions } from "svelte-dnd-action";
    import type { Task } from "$lib/apiClient";
    import TaskCard from "$lib/components/TaskCard.svelte";

    export let title: string;
    export let tasks: Task[] = [];
    export let zoneOptions: DndZoneOptions<DndItem> | undefined;

    const dispatch = createEventDispatcher<{
        consider: DndEvent<Task>;
        finalize: DndEvent<Task>;
        select: { task: Task };
        complete: { task: Task };
    }>();

    const forward =
        (type: "consider" | "finalize") =>
        (event: CustomEvent<DndEvent<DndItem>>) =>
            dispatch(type, event.detail as DndEvent<Task>);

    const forwardSelect = (event: CustomEvent<{ task: Task }>) => {
        dispatch("select", event.detail);
    };

    const forwardComplete = (event: CustomEvent<{ task: Task }>) => {
        dispatch("complete", event.detail);
    };

    $: resolvedOptions =
        zoneOptions ??
        ({
            id: `column-${title ?? "task"}`,
            items: tasks,
            getItemId: (item: DndItem) => item.id,
        } satisfies DndZoneOptions<DndItem>);
</script>

<div
    class="flex flex-col bg-white rounded-2xl w-full border border-gray-200 shadow-sm"
    use:dndzone={resolvedOptions}
    on:consider={forward("consider")}
    on:finalize={forward("finalize")}
>
    <header class="flex items-center justify-between px-4 py-2 border-b border-gray-100">
        <div class="flex items-center gap-2">
            <h2 class="text-sm text-gray-700 font-semibold uppercase tracking-wide">{title}</h2>
            <span class="text-xs text-gray-500 bg-gray-100 px-2 py-0.5 rounded-full">{tasks.length}</span>
        </div>
    </header>

    <div class="flex flex-col space-y-2 overflow-y-auto max-h-[70vh] p-3">
        {#if tasks.length > 0}
            {#each tasks as task (task.id)}
                <TaskCard
                    {task}
                    showCompleteButton
                    on:select={forwardSelect}
                    on:complete={forwardComplete}
                />
            {/each}
        {:else}
            <div class="text-sm text-gray-400 italic">No tasks yet.</div>
        {/if}
    </div>
</div>
