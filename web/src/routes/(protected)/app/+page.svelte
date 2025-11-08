<script lang="ts">
    import { env as publicEnv } from "$env/dynamic/public";
    import type { AuthStatus, Task } from "$lib/apiClient";
    import Header from "$lib/components/Header.svelte";
    import Timeline from "$lib/components/Timeline.svelte";
    import TaskBoard from "$lib/components/TaskBoard.svelte";
    import TaskToolbar from "$lib/components/TaskToolbar.svelte";
    import CreateTaskModal from "$lib/components/CreateTaskModal.svelte";

    export let data: {
        tasks: Array<Task>;
        auth: AuthStatus;
        error?: string;
    };

    const API_URL_EXTERNAL = publicEnv.PUBLIC_API_ORIGIN;
    const APP_URL_EXTERNAL = publicEnv.PUBLIC_APP_ORIGIN;

    const LOGOUT_URL = `${API_URL_EXTERNAL}/auth/logout?return_to=${encodeURIComponent(APP_URL_EXTERNAL + "/")}`;
    function handleLogout() {
        window.location.href = LOGOUT_URL;
    }

    let showCreate = false;
</script>

<Header userName={data.auth.user?.name} onLogout={handleLogout} />

{#if data?.error}
    <p style="color: crimson;">Error loading tasks: {data.error}</p>
{/if}

<!-- The Create form lives in the modal -->
<CreateTaskModal
    open={showCreate}
    title="Create Task"
    on:close={() => (showCreate = false)}
>
    <form
        method="POST"
        action="?/create"
        class="grid grid-cols-1 gap-4 w-full max-w-md mx-auto p-2"
    >
        <input
            name="title"
            placeholder="Task title"
            required
            class="border rounded px-2 py-1"
        />
        <textarea
            name="description"
            placeholder="Description (optional)"
            rows="3"
            class="border rounded px-2 py-1"
        ></textarea>
        <div class="flex gap-2">
            <button
                type="submit"
                class="px-4 py-2 bg-blue-500 text-white rounded">Create</button
            >
            <button
                type="button"
                class="px-4 py-2"
                on:click={() => (showCreate = false)}>Cancel</button
            >
        </div>
    </form>
</CreateTaskModal>

<div class="flex justify-center">
    <div class="flex flex-col w-full max-w-7xl px-4">
        <Timeline />
        <div class="mt-6">
            <TaskToolbar on:newTask={() => (showCreate = true)} />
        </div>
        <TaskBoard on:taskClick={handleTaskCardClick} tasks={data.tasks} />
    </div>
</div>
