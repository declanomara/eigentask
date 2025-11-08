<script lang="ts">
    import { createEventDispatcher } from "svelte";
    import type { Task } from "$lib/apiClient";

    export let task: Task;

    const dispatch = createEventDispatcher();

    function handleTaskClick() {
        dispatch("taskClick", { task: task });
    }
</script>

<div
    class="bg-white rounded-xl border border-gray-200 p-4 hover:shadow-md transition-shadow cursor-pointer flex flex-col gap-2"
    on:click={handleTaskClick}
>
    <!-- Title -->
    <h3 class="font-semibold text-gray-800 text-base leading-tight">
        {task.title}
    </h3>

    <!-- Optional Description -->
    {#if task.description}
        <p class="text-sm text-gray-500 line-clamp-2">{task.description}</p>
    {/if}
</div>
