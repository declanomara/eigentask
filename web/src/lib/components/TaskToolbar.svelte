<script lang="ts">
    import { createEventDispatcher } from "svelte";
    const dispatch = createEventDispatcher();

    function onNewTask() {
        dispatch("newTask");
    }
</script>

<div class="flex justify-end">
    <button
        on:click={onNewTask}
        class="outline-1 outline-gray-300 text-gray-300 hover:bg-blue-600 hover:text-white rounded-xl cursor-pointer p-2 mx-2 max-w-8 max-h-8"
        aria-label="Create new task"
        title="Create new task"
    >
        <svg
            xmlns="http://www.w3.org/2000/svg"
            class="h-4 w-4"
            viewBox="0 0 24 24"
            fill="none"
            stroke="currentColor"
            stroke-width="2"
            aria-hidden="true"
        >
            <path d="M12 20h9" />
            <path d="M16.5 3.5a2.121 2.121 0 013 3L7 19l-4 1 1-4 9-9z" />
        </svg>
    </button>
</div>
