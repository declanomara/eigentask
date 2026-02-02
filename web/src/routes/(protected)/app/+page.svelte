<script lang="ts">
    import { browser } from "$app/environment";
    import { onMount } from "svelte";
    import { env as publicEnv } from "$env/dynamic/public";
    import { createApiClient, type AuthStatus, type Task, type SessionWithTask } from "$lib/apiClient";
    import CreateTaskForm from "$lib/components/CreateTaskForm.svelte";
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
    let sessionsForDay: SessionWithTask[] = [];
    let showCreate = false;
    let showEdit = false;
    let selectedTask: Task | null = null;
    let banner: string | null = data.error ?? null;
    let selectedDate = startOfDay(new Date());
    let isMounted = false;

    async function fetchSessionsForDay() {
        const start = timelineDayStart();
        const end = timelineDayEnd();
        const res = await api.getSessionsInRange(start.toISOString(), end.toISOString());
        sessionsForDay = res.ok && res.sessions ? res.sessions : [];
    }
    $: if (browser) {
        selectedDate;
        fetchSessionsForDay();
    }

    onMount(() => {
        isMounted = true;
    });

    async function refreshTasksAndSessions() {
        await fetchSessionsForDay();
        const tasksRes = await api.getTasks();
        if (tasksRes.ok && tasksRes.tasks) tasks = tasksRes.tasks;
    }

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

    const pendingSessionsCount = (task: Task) =>
        Math.max(0, (task.sessions_count ?? 0) - (task.completed_sessions_count ?? 0));

    const effectiveStatus = (task: Task) => {
        if (task.status === "COMPLETED") return "COMPLETED";
        if (task.status === "REMOVED") return "REMOVED";
        return pendingSessionsCount(task) > 0 ? "PLANNED" : "BACKLOG";
    };

    const startMillis = (task: Task) => parseDate(task.planned_start_at)?.getTime() ?? Number.MAX_SAFE_INTEGER;

    $: backlogTasks = tasks.filter((t) => {
        const status = effectiveStatus(t);
        return status === "BACKLOG" || status === "REMOVED";
    });
    $: scheduledTasks = tasks
        .filter((t) => effectiveStatus(t) === "PLANNED")
        .sort((a, b) => startMillis(a) - startMillis(b));
    $: completedTasks = tasks.filter((t) => effectiveStatus(t) === "COMPLETED");

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
        const sessionsRes = await api.getSessionsForTask(taskId);
        if (!sessionsRes.ok || !sessionsRes.sessions) {
            banner = sessionsRes.error ?? "Unable to load sessions for completion.";
            return;
        }
        const now = Date.now();
        for (const session of sessionsRes.sessions) {
            const start = new Date(session.scheduled_start_at).getTime();
            if (Number.isNaN(start)) continue;
            if (start <= now) {
                if (session.status !== "COMPLETED") {
                    const res = await api.updateSession(taskId, session.id, { status: "COMPLETED" });
                    if (!res.ok) {
                        banner = res.error ?? "Unable to complete past sessions.";
                        return;
                    }
                }
            } else {
                const res = await api.deleteSession(taskId, session.id);
                if (!res.ok) {
                    banner = res.error ?? "Unable to remove future sessions.";
                    return;
                }
            }
        }
        const res = await api.updateTask(taskId, { status: "COMPLETED" });
        if (!res.ok || !res.task) {
            banner = res.error ?? "Unable to complete the task.";
            return;
        }
        banner = null;
        await refreshTasksAndSessions();
    }

    async function reopenTask(taskId: number) {
        const task = tasks.find((t) => t.id === taskId);
        if (!task || task.status !== "COMPLETED") return;

        const shouldReschedule = pendingSessionsCount(task) > 0;
        const res = await api.updateTask(taskId, { status: shouldReschedule ? "PLANNED" : "BACKLOG" });
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

    function handleGlobalKeydown(event: KeyboardEvent) {
        const key = event.key.toLowerCase();
        if (key !== "n" || event.ctrlKey || event.shiftKey || event.altKey) return;
        const target = event.target as HTMLElement | null;
        if (target && (target.closest("input, textarea, select") || target.isContentEditable)) return;
        event.preventDefault();
        if (!showCreate && !showEdit) {
            showCreate = true;
        }
    }

    function clampToAvailableSlot(
        startAt: Date,
        durationMinutes: number,
        excludeSessionId: number | null,
    ) {
        const startBound = timelineDayStart();
        const endBound = timelineDayEnd();
        const durationMs = durationMinutes * 60000;
        const windowStart = startBound.getTime();
        const windowEnd = endBound.getTime();
        const intervals = sessionsForDay
            .filter((s) => excludeSessionId === null || s.id !== excludeSessionId)
            .map((s) => {
                const sStart = parseDate(s.scheduled_start_at);
                const sEnd = parseDate(s.scheduled_end_at);
                if (!sStart || !sEnd) return null;
                return [sStart.getTime(), sEnd.getTime()] as const;
            })
            .filter((s): s is readonly [number, number] => Boolean(s))
            .sort((a, b) => a[0] - b[0]);

        const gaps: Array<[number, number]> = [];
        let cursor = windowStart;
        for (const [sStart, sEnd] of intervals) {
            if (sEnd <= cursor) continue;
            if (sStart > cursor) {
                gaps.push([cursor, Math.min(sStart, windowEnd)]);
            }
            cursor = Math.max(cursor, sEnd);
            if (cursor >= windowEnd) break;
        }
        if (cursor < windowEnd) gaps.push([cursor, windowEnd]);

        let bestStart: number | null = null;
        let bestDistance = Number.POSITIVE_INFINITY;
        for (const [gapStart, gapEnd] of gaps) {
            if (gapEnd - gapStart < durationMs) continue;
            const minStart = gapStart;
            const maxStart = gapEnd - durationMs;
            const candidate = Math.min(Math.max(startAt.getTime(), minStart), maxStart);
            const distance = Math.abs(candidate - startAt.getTime());
            if (distance < bestDistance) {
                bestDistance = distance;
                bestStart = candidate;
            }
        }
        if (bestStart === null) {
            return clampToBounds(startAt, durationMinutes);
        }
        return new Date(bestStart);
    }

    async function scheduleTask(taskId: number, startAt: Date) {
        const task = tasks.find((t) => t.id === taskId);
        if (!task) return;
        const duration = toDuration(task);
        const clampedStart = clampToBounds(startAt, duration);
        const finalStart = overlapsSession(clampedStart, duration, null)
            ? clampToAvailableSlot(clampedStart, duration, null)
            : clampedStart;
        const endAt = new Date(finalStart.getTime() + duration * 60000);
        const res = await api.createSession(taskId, {
            scheduled_start_at: finalStart.toISOString(),
            scheduled_end_at: endAt.toISOString(),
        });
        if (!res.ok) {
            banner = res.error ?? "Unable to schedule the session.";
            return;
        }
        banner = null;
        await refreshTasksAndSessions();
    }

    async function rescheduleSession(session: SessionWithTask, startAt: Date, durationMinutes: number) {
        const clampedStart = clampToBounds(startAt, durationMinutes);
        const finalStart = overlapsSession(clampedStart, durationMinutes, session.id)
            ? clampToAvailableSlot(clampedStart, durationMinutes, session.id)
            : clampedStart;
        const endAt = new Date(finalStart.getTime() + durationMinutes * 60000);
        const res = await api.updateSession(session.task_id, session.id, {
            scheduled_start_at: finalStart.toISOString(),
            scheduled_end_at: endAt.toISOString(),
        });
        if (!res.ok) {
            banner = res.error ?? "Unable to reschedule the session.";
            return;
        }
        banner = null;
        await refreshTasksAndSessions();
    }

    function overlapsSession(start: Date, durationMinutes: number, excludeSessionId: number | null): boolean {
        const end = new Date(start.getTime() + durationMinutes * 60000);
        return sessionsForDay.some((s) => {
            if (excludeSessionId !== null && s.id === excludeSessionId) return false;
            const sStart = parseDate(s.scheduled_start_at);
            const sEnd = parseDate(s.scheduled_end_at);
            if (!sStart || !sEnd) return false;
            return start < sEnd && sStart < end;
        });
    }

    async function unscheduleSession(session: SessionWithTask) {
        const res = await api.deleteSession(session.task_id, session.id);
        if (!res.ok) {
            banner = res.error ?? "Unable to unschedule.";
            return;
        }
        banner = null;
        await refreshTasksAndSessions();
    }

    function handleTaskSaved(event: CustomEvent<{ task: Task }>) {
        replaceTask(event.detail.task);
        banner = null;
        handleEditClose();
    }

    async function handleTaskDeleted(event: CustomEvent<{ id: number }>) {
        removeTask(event.detail.id);
        sessionsForDay = sessionsForDay.filter((s) => s.task_id !== event.detail.id);
        banner = null;
        handleEditClose();
        await refreshTasksAndSessions();
    }

    function handleSchedule(event: CustomEvent<{ taskId: number; startAt: Date }>) {
        scheduleTask(event.detail.taskId, event.detail.startAt);
    }

    function handleBoardFinalize(event: CustomEvent<DndEvent<Task | SessionWithTask>>) {
        const sourceId = event.detail.info.source?.id;
        const destId = event.detail.info.destination?.id;
        const dragged = event.detail.info.source?.item;
        if (!dragged) return;
        if (destId === "backlog" && sourceId === "timeline") {
            const session = dragged as SessionWithTask;
            if ("task_id" in session && "scheduled_start_at" in session) {
                unscheduleSession(session);
                return;
            }
        }
        if (destId === "backlog" && sourceId !== "backlog") {
            const task = dragged as Task;
            if ("status" in task && !("scheduled_start_at" in task && "task_id" in task)) {
                unscheduleTask(task.id);
            }
        }
    }

    async function unscheduleTask(taskId: number) {
        const sessionsRes = await api.getSessionsForTask(taskId);
        if (!sessionsRes.ok || !sessionsRes.sessions) {
            banner = sessionsRes.error ?? "Unable to load sessions for unscheduling.";
            return;
        }
        const incomplete = sessionsRes.sessions.filter((s) => s.status === "INCOMPLETE");
        for (const session of incomplete) {
            const res = await api.deleteSession(taskId, session.id);
            if (!res.ok) {
                banner = res.error ?? "Unable to unschedule.";
                return;
            }
        }
        banner = null;
        await fetchSessionsForDay();
        const tasksRes = await api.getTasks();
        if (tasksRes.ok && tasksRes.tasks) tasks = tasksRes.tasks;
    }

    function handleComplete(event: CustomEvent<{ task: Task }>) {
        completeTask(event.detail.task.id);
    }

    function handleReopen(event: CustomEvent<{ task: Task }>) {
        reopenTask(event.detail.task.id);
    }

    async function completeSession(session: SessionWithTask) {
        const res = await api.updateSession(session.task_id, session.id, { status: "COMPLETED" });
        if (!res.ok) {
            banner = res.error ?? "Unable to complete session.";
            return;
        }
        banner = null;
        await refreshTasksAndSessions();
    }

    async function completeNextSessionForTask(task: Task) {
        const res = await api.getSessionsForTask(task.id);
        if (!res.ok || !res.sessions) return;
        const incomplete = res.sessions
            .filter((s) => s.status === "INCOMPLETE")
            .sort((a, b) => new Date(a.scheduled_start_at).getTime() - new Date(b.scheduled_start_at).getTime());
        const next = incomplete[0];
        if (!next) return;
        await completeSession({ ...next, task_title: task.title });
    }
</script>

<svelte:window on:keydown={handleGlobalKeydown} />

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
    <CreateTaskForm
        on:close={() => (showCreate = false)}
        on:created={(e) => {
            tasks = [...tasks, e.detail.task];
            banner = null;
            showCreate = false;
        }}
    />
</CreateTaskModal>

<TaskEditDrawer
    open={showEdit}
    task={selectedTask}
    on:close={handleEditClose}
    on:saved={handleTaskSaved}
    on:deleted={handleTaskDeleted}
    on:sessionsChanged={refreshTasksAndSessions}
/>

<div class="flex justify-center">
    <div class="flex flex-col w-full max-w-7xl px-4 py-6 space-y-6">
        {#if isMounted}
            <Timeline
                bind:date={selectedDate}
                startHour={timelineStartHour}
                endHour={timelineEndHour}
                tasks={tasks}
                sessions={sessionsForDay}
                defaultDuration={defaultDuration}
                on:schedule={handleSchedule}
                on:select={handleTaskSelect}
                on:completeSession={({ detail }: CustomEvent<{ session: SessionWithTask }>) => completeSession(detail.session)}
                on:rescheduleSession={(
                    { detail }: CustomEvent<{ session: SessionWithTask; startAt: Date; duration: number }>,
                ) => rescheduleSession(detail.session, detail.startAt, detail.duration)}
            />
        {:else}
            <section class="flex flex-col border border-border rounded-2xl bg-surface shadow-sm p-6 gap-4">
                <div class="h-36 rounded-xl border border-dashed border-border bg-surface"></div>
            </section>
        {/if}
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
            on:completeNextSession={({ detail }: CustomEvent<{ task: Task }>) => completeNextSessionForTask(detail.task)}
        />
    </div>
</div>
