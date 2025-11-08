<script lang="ts">
    import type { Task } from "$lib/apiClient";
    import TaskCard from "$lib/components/TaskCard.svelte";

    export let title;
    export let tasks: Task[] = [];
</script>

<div class="flex flex-col bg-gray-50 rounded-2xl w-full border-gray-300 border">
    <!-- Column Header -->
    <h2 class="text-sm text-gray-400 font-mono px-4 py-1">{title}</h2>
    <hr class="text-gray-300 w-full" />

    <!-- Task List -->
    <div class="flex flex-col space-y-2 overflow-y-auto max-h-[70vh] p-2">
        {#if tasks.length > 0}
            {#each tasks as task (task.id)}
                <TaskCard {task} />
            {/each}
        {:else}
            <div class="text-sm text-grey-500">No tasks.</div>
        {/if}
    </div>
</div>
