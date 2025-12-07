<script lang="ts">
    import { env as publicEnv } from "$env/dynamic/public";
    import { createApiClient, type AuthStatus, type Task } from "$lib/apiClient";
    import CreateTaskModal from "$lib/components/CreateTaskModal.svelte";
    import Header from "$lib/components/Header.svelte";
    import TaskBoard from "$lib/components/TaskBoard.svelte";
    import TaskEditDrawer from "$lib/components/TaskEditDrawer.svelte";
    import TaskToolbar from "$lib/components/TaskToolbar.svelte";
    import Timeline from "$lib/components/Timeline.svelte";
    import type { DndEvent } from "svelte-dnd-action";

    export let data: {
        tasks: Array<Task>;
        auth: AuthStatus;
        error?: string | null;
    };

    const api = createApiClient({
        internalBaseUrl: publicEnv.PUBLIC_API_ORIGIN ?? "",
        externalBaseUrl: publicEnv.PUBLIC_API_ORIGIN ?? "",
    });

    const APP_URL_EXTERNAL = publicEnv.PUBLIC_APP_ORIGIN ?? "";
    const LOGOUT_URL = `${api.externalBaseUrl}/auth/logout?return_to=${encodeURIComponent(APP_URL_EXTERNAL + "/")}`;

    const defaultDuration = 60;
    const timelineStartHour = 8;
    const timelineEndHour = 18;

    const startOfDay = (date: Date) => {
        const d = new Date(date);
        d.setHours(0, 0, 0, 0);
        return d;
    };

    let tasks: Task[] = data.tasks ?? [];
    let showCreate = false;
    let showEdit = false;
    let selectedTask: Task | null = null;
    let banner: string | null = data.error ?? null;
    let selectedDate = startOfDay(new Date());

    const parseDate = (value: string | null) => (value ? new Date(value) : null);

    const isSameDay = (value: string | null, target: Date) => {
        if (!value) return false;
        const d = parseDate(value);
        if (!d) return false;
        return (
            d.getFullYear() === target.getFullYear() &&
            d.getMonth() === target.getMonth() &&
            d.getDate() === target.getDate()
        );
    };

    $: backlogTasks = tasks.filter((t) => t.status === "BACKLOG" || t.status === "REMOVED");
    $: scheduledTasks = tasks.filter((t) => t.status === "PLANNED");
    $: completedTasks = tasks.filter((t) => t.status === "COMPLETED");
    $: timelineTasks = tasks.filter((t) => t.status === "PLANNED" || t.status === "COMPLETED");

    const timelineDayStart = () => {
        const d = startOfDay(selectedDate);
        d.setHours(timelineStartHour, 0, 0, 0);
        return d;
    };

    const timelineDayEnd = () => {
        const d = startOfDay(selectedDate);
        d.setHours(timelineEndHour, 0, 0, 0);
        return d;
    };

    const toDuration = (task: Task) => task.planned_duration ?? defaultDuration;

    const overlaps = (taskId: number, start: Date, durationMinutes: number) => {
        const end = new Date(start.getTime() + durationMinutes * 60000);
        return scheduledTasks.some((t) => {
            if (t.id === taskId) return false;
            if (!isSameDay(t.planned_start_at, selectedDate)) return false;
            const otherStart = parseDate(t.planned_start_at);
            const otherEnd =
                parseDate(t.planned_end_at) ??
                (otherStart ? new Date(otherStart.getTime() + toDuration(t) * 60000) : null);
            if (!otherStart || !otherEnd) return false;
            return start < otherEnd && otherStart < end;
        });
    };

    const clampToBounds = (startAt: Date, durationMinutes: number) => {
        const startBound = timelineDayStart();
        const endBound = timelineDayEnd();
        const latestStart = new Date(Math.max(startBound.getTime(), endBound.getTime() - durationMinutes * 60000));
        const candidate = new Date(Math.max(startAt.getTime(), startBound.getTime()));
        return candidate > latestStart ? latestStart : candidate;
    };

    const replaceTask = (updated: Task) => {
        tasks = tasks.map((t) => (t.id === updated.id ? updated : t));
    };

    const removeTask = (id: number) => {
        tasks = tasks.filter((t) => t.id !== id);
    };

    function handleLogout() {
        window.location.href = LOGOUT_URL;
    }

    function handleTaskSelect(event: CustomEvent<{ task: Task }>) {
        selectedTask = event.detail.task;
        showEdit = true;
    }

    async function completeTask(taskId: number) {
        const task = tasks.find((t) => t.id === taskId);
        if (!task || task.status === "COMPLETED") return;
        const res = await api.updateTask(taskId, { status: "COMPLETED" });
        if (!res.ok || !res.task) {
            banner = res.error ?? "Unable to complete the task.";
            return;
        }
        banner = null;
        replaceTask(res.task);
    }

    async function reopenTask(taskId: number) {
        const task = tasks.find((t) => t.id === taskId);
        if (!task || task.status !== "COMPLETED") return;

        // If it still has scheduled times, restore to PLANNED; otherwise send to BACKLOG.
        const shouldReschedule = Boolean(task.planned_start_at);
        const payload = shouldReschedule
            ? {
                  status: "PLANNED" as const,
                  planned_start_at: task.planned_start_at,
                  planned_end_at: task.planned_end_at,
                  planned_duration: task.planned_duration,
              }
            : {
                  status: "BACKLOG" as const,
                  planned_start_at: null,
                  planned_end_at: null,
              };

        const res = await api.updateTask(taskId, payload);
        if (!res.ok || !res.task) {
            banner = res.error ?? "Unable to reopen the task.";
            return;
        }
        banner = null;
        replaceTask(res.task);
    }

    function handleEditClose() {
        showEdit = false;
        selectedTask = null;
    }

    async function scheduleTask(taskId: number, startAt: Date) {
        const task = tasks.find((t) => t.id === taskId);
        if (!task) return;
        const duration = toDuration(task);
        const clampedStart = clampToBounds(startAt, duration);
        if (overlaps(taskId, clampedStart, duration)) {
            banner = "That time overlaps another scheduled task.";
            return;
        }
        const endAt = new Date(clampedStart.getTime() + duration * 60000);
        const res = await api.updateTask(taskId, {
            status: "PLANNED",
            planned_start_at: clampedStart.toISOString(),
            planned_end_at: endAt.toISOString(),
            planned_duration: duration,
        });
        if (!res.ok || !res.task) {
            banner = res.error ?? "Unable to schedule the task.";
            return;
        }
        banner = null;
        replaceTask(res.task);
    }

    async function unscheduleTask(taskId: number) {
        const res = await api.updateTask(taskId, {
            status: "BACKLOG",
            planned_start_at: null,
            planned_end_at: null,
        });
        if (!res.ok || !res.task) {
            banner = res.error ?? "Unable to move task to backlog.";
            return;
        }
        banner = null;
        replaceTask(res.task);
    }

    function handleTaskSaved(event: CustomEvent<{ task: Task }>) {
        replaceTask(event.detail.task);
        banner = null;
        handleEditClose();
    }

    function handleTaskDeleted(event: CustomEvent<{ id: number }>) {
        removeTask(event.detail.id);
        banner = null;
        handleEditClose();
    }

    function handleSchedule(event: CustomEvent<{ taskId: number; startAt: Date }>) {
        scheduleTask(event.detail.taskId, event.detail.startAt);
    }

    function handleBoardFinalize(event: CustomEvent<DndEvent<Task>>) {
        const sourceId = event.detail.info.source?.id;
        const destId = event.detail.info.destination?.id;
        const dragged = event.detail.info.source?.item;
        if (!dragged) return;
        if (destId === "backlog" && sourceId !== "backlog") {
            unscheduleTask(dragged.id as number);
        }
    }

    function handleComplete(event: CustomEvent<{ task: Task }>) {
        completeTask(event.detail.task.id);
    }

    function handleReopen(event: CustomEvent<{ task: Task }>) {
        reopenTask(event.detail.task.id);
    }
</script>

<Header userName={data.auth.user?.name} onLogout={handleLogout} />

{#if banner}
    <div class="fixed top-4 inset-x-0 flex justify-center z-50 pointer-events-none">
        <div class="max-w-3xl pointer-events-auto rounded-lg border border-amber-200 bg-amber-50 px-4 py-3 text-amber-800 shadow-md">
            {banner}
        </div>
    </div>
{/if}

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
        <label class="flex flex-col gap-1 text-sm text-gray-700">
            Estimated minutes
            <input
                name="planned_duration"
                type="number"
                min="15"
                step="15"
                value="60"
                class="border rounded px-2 py-1"
            />
        </label>
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

<TaskEditDrawer
    open={showEdit}
    task={selectedTask}
    on:close={handleEditClose}
    on:saved={handleTaskSaved}
    on:deleted={handleTaskDeleted}
/>

<div class="flex justify-center">
    <div class="flex flex-col w-full max-w-7xl px-4 py-6 space-y-6">
        <Timeline
            bind:date={selectedDate}
            startHour={timelineStartHour}
            endHour={timelineEndHour}
            tasks={timelineTasks}
            defaultDuration={defaultDuration}
            on:schedule={handleSchedule}
            on:select={handleTaskSelect}
        />
        <div class="flex items-center justify-between">
            <div class="text-sm text-gray-500">
                Drag backlog items onto the timeline to schedule them. Drag a scheduled item back to
                the backlog column to unschedule.
            </div>
            <TaskToolbar on:newTask={() => (showCreate = true)} />
        </div>
        <TaskBoard
            backlogTasks={backlogTasks}
            scheduledTasks={scheduledTasks}
            completedTasks={completedTasks}
            on:finalize={handleBoardFinalize}
            on:select={handleTaskSelect}
            on:complete={handleComplete}
            on:reopen={handleReopen}
        />
    </div>
</div>
