<script lang="ts">
    import { createEventDispatcher } from "svelte";
    import type { Task } from "$lib/apiClient";
    import type { DndEvent, DndZoneOptions } from "svelte-dnd-action";
    import TaskColumn from "./TaskColumn.svelte";

    export let backlogTasks: Task[] = [];
    export let scheduledTasks: Task[] = [];

    const dispatch = createEventDispatcher<{
        consider: DndEvent<Task>;
        finalize: DndEvent<Task>;
        select: { task: Task };
    }>();

    $: backlogOptions = { id: "backlog", items: backlogTasks } satisfies DndZoneOptions<Task>;
    $: scheduledOptions = { id: "scheduled", items: scheduledTasks } satisfies DndZoneOptions<Task>;

    function forward(event: CustomEvent<DndEvent<Task>>) {
        dispatch(event.type as "consider" | "finalize", event.detail);
    }

    function forwardSelect(event: CustomEvent<{ task: Task }>) {
        dispatch("select", event.detail);
    }
</script>

<div class="grid grid-cols-1 md:grid-cols-2 gap-4 p-2 w-full">
    <TaskColumn
        title="Backlog"
        tasks={backlogTasks}
        zoneOptions={backlogOptions}
        on:consider={forward}
        on:finalize={forward}
        on:select={forwardSelect}
    />
    <TaskColumn
        title="Scheduled"
        tasks={scheduledTasks}
        zoneOptions={scheduledOptions}
        on:consider={forward}
        on:finalize={forward}
        on:select={forwardSelect}
    />
</div>
