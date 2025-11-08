<script lang="ts">
    import TaskColumn from "./TaskColumn.svelte";
    import type { Task } from "$lib/apiClient";
    export let tasks: Task[];
</script>

<div class="flex gap-4 p-2 overflow-x-auto w-full">
    <TaskColumn title="Backlog" {tasks} />
    <TaskColumn title="Scheduled" {tasks} />
</div>
