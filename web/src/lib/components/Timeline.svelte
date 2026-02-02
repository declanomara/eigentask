<script lang="ts">
    import { createEventDispatcher } from "svelte";
    import { dndzone, type DndEvent, type DndZoneOptions } from "svelte-dnd-action";
    import type { Task, SessionWithTask } from "$lib/apiClient";

    export let startHour = 8;
    export let endHour = 18;
    export let slotMinutes = 15;
    export let date: Date = new Date();
    export let tasks: Task[] = [];
    export let sessions: SessionWithTask[] = [];
    export let defaultDuration = 60;

    const BAR_TOP_PERCENT = 20;
    const BAR_HEIGHT_PERCENT = 70;

    const SHORT_TASK_MINUTES = 45;
    const SHORT_LABEL_LANES = 3;
    const SHORT_LABEL_VERTICAL_GAP = 14;
    const SHORT_LABEL_BASE_OFFSET = 4;
    const SHORT_LABEL_LINE_GAP = 6;
    const SHORT_LABEL_TEXT_HEIGHT = 14;

    const dispatch = createEventDispatcher<{
        schedule: { taskId: number; startAt: Date };
        select: { task: Task };
        completeSession: { session: SessionWithTask };
        unscheduleSession: { session: SessionWithTask };
        rescheduleSession: { session: SessionWithTask; startAt: Date; duration: number };
    }>();

    const DEBUG = false;

    let trackEl: HTMLDivElement | null = null;
    let previewStartMinutes: number | null = null;
    let previewDuration: number | null = null;
    let ticks: number[] = [];
    let visibleSessions: SessionWithTask[] = [];
    let debugMessage = "";
    let shortTaskLaneMap = new Map<number, number>();
    let resizingSessionId: number | null = null;
    let resizeEdge: "start" | "end" | null = null;
    let resizeStartMinutes: number | null = null;
    let resizeDurationMinutes: number | null = null;
    let resizePointerMinutes: number | null = null;
    let committedResize: { sessionId: number; start: number; duration: number } | null = null;
    $: isResizing = resizingSessionId !== null;

    $: resizePreview =
        resizingSessionId !== null &&
        resizeEdge !== null &&
        resizeStartMinutes !== null &&
        resizeDurationMinutes !== null
            ? (() => {
                  const pointer =
                      resizePointerMinutes ??
                      (resizeEdge === "start"
                          ? resizeStartMinutes
                          : resizeStartMinutes + resizeDurationMinutes);
                  return computeResizeRange(
                      resizeStartMinutes,
                      resizeDurationMinutes,
                      pointer,
                      resizeEdge,
                      resizingSessionId,
                  );
              })()
            : null;

    $: totalMinutes = Math.max(0, (endHour - startHour) * 60);
    $: hours = Math.max(0, endHour - startHour);
    $: ticks = Array.from({ length: Math.floor((hours * 60) / slotMinutes) + 1 }, (_, i) => i as number);
    const sessionStartMillis = (s: SessionWithTask) => new Date(s.scheduled_start_at).getTime();
    $: visibleSessions = [...sessions]
        .filter((session) => tasks.some((task) => task.id === session.task_id))
        .sort((a, b) => sessionStartMillis(a) - sessionStartMillis(b));

    $: shortTaskLaneMap = (() => {
        const map = new Map<number, number>();
        const shortSessions = visibleSessions
            .filter((s) => getDurationSession(s) < SHORT_TASK_MINUTES)
            .sort((a, b) => sessionStartMillis(a) - sessionStartMillis(b));
        shortSessions.forEach((s, index) => {
            map.set(s.id, index % SHORT_LABEL_LANES);
        });
        return map;
    })();

    const isSameDayDate = (value: Date, target: Date) =>
        value.getFullYear() === target.getFullYear() &&
        value.getMonth() === target.getMonth() &&
        value.getDate() === target.getDate();

    $: isTodaySelected = isSameDayDate(date, new Date());
    $: nowLineMinutes = (() => {
        if (!isTodaySelected || totalMinutes === 0) return null;
        const now = new Date();
        const minutes = (now.getHours() - startHour) * 60 + now.getMinutes();
        if (minutes < 0 || minutes > totalMinutes) return null;
        return clampMinutes(minutes);
    })();
    $: zoneOptions = {
        id: "timeline",
        items: visibleSessions,
    } satisfies DndZoneOptions<SessionWithTask>;

    const setDate = (delta: number) => {
        date = new Date(date);
        date.setDate(date.getDate() + delta);
    };

    const incrementDate = () => setDate(1);
    const decrementDate = () => setDate(-1);

    const isSameDay = (value: string | null, target: Date) => {
        if (!value) return false;
        const d = new Date(value);
        return (
            d.getFullYear() === target.getFullYear() &&
            d.getMonth() === target.getMonth() &&
            d.getDate() === target.getDate()
        );
    };

    const startOfDay = (d: Date) => {
        const copy = new Date(d);
        copy.setHours(startHour, 0, 0, 0);
        return copy;
    };

    const clampMinutes = (minutes: number) => Math.min(Math.max(minutes, 0), totalMinutes);

    const snapMinutes = (minutes: number) =>
        Math.round(minutes / slotMinutes) * slotMinutes;

    const parseDate = (value: string | null) => (value ? new Date(value) : null);

    const getStartMinutesSession = (s: SessionWithTask) => {
        const start = parseDate(s.scheduled_start_at);
        if (!start) return 0;
        return clampMinutes((start.getHours() - startHour) * 60 + start.getMinutes());
    };

    const getDurationSession = (s: SessionWithTask) => {
        const start = parseDate(s.scheduled_start_at);
        const end = parseDate(s.scheduled_end_at);
        if (start && end) return clampMinutes(Math.max(0, (end.getTime() - start.getTime()) / 60000));
        return 0;
    };

    const getStartMinutes = (task: Task) => {
        if (!task.planned_start_at) return 0;
        const start = parseDate(task.planned_start_at);
        if (!start) return 0;
        return clampMinutes((start.getHours() - startHour) * 60 + start.getMinutes());
    };

    const getDuration = (task: Task) => {
        const start = parseDate(task.planned_start_at);
        const end = parseDate(task.planned_end_at);
        if (start && end) return clampMinutes(Math.max(0, (end.getTime() - start.getTime()) / 60000));
        return clampMinutes(task.planned_duration ?? defaultDuration);
    };

    const isShortTask = (task: Task) => getDuration(task) < SHORT_TASK_MINUTES;
    const isShortSession = (s: SessionWithTask) => getDurationSession(s) < SHORT_TASK_MINUTES;

    const formatTimeRangeSession = (s: SessionWithTask) => {
        const start = parseDate(s.scheduled_start_at);
        const end = parseDate(s.scheduled_end_at);
        if (!start || !end) return "";
        return `${start.toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" })} — ${end.toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" })}`;
    };

    const formatTimeRange = (task: Task) => {
        const start = parseDate(task.planned_start_at);
        const explicitEnd = parseDate(task.planned_end_at);
        const rawDuration = task.planned_duration ?? defaultDuration;
        const inferredEnd = start ? new Date(start.getTime() + rawDuration * 60000) : null;
        const end = explicitEnd ?? inferredEnd;
        if (!start || !end) return "";
        return `${start.toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" })} — ${end.toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" })}`;
    };

    const sessionStatusLabel = (s: SessionWithTask) => (s.status === "COMPLETED" ? "Completed" : "Scheduled");

    const getTaskForSession = (s: SessionWithTask): Task | undefined => tasks.find((t) => t.id === s.task_id);

    const toPercent = (minutes: number) =>
        totalMinutes === 0 ? 0 : (minutes / totalMinutes) * 100;

    const formatHourLabel = (tickIndex: number) => {
        const hour = startHour + Math.floor((tickIndex * slotMinutes) / 60);
        return `${hour.toString().padStart(2, "0")}:00`;
    };

    const log = (label: string, data: Record<string, unknown>) => {
        if (!DEBUG) return;
        debugMessage = `${label}: ${JSON.stringify(data)}`;
        // eslint-disable-next-line no-console
        console.log("[timeline]", label, data);
    };

    const blockToneSession = (s: SessionWithTask) =>
        s.status === "COMPLETED"
            ? "bg-gray-300 text-gray-800 ring-border/80 border border-border"
            : "bg-blue-500 text-white ring-blue-200/80";

    const blockTone = (task: Task) =>
        task.status === "COMPLETED"
            ? "bg-gray-300 text-gray-800 ring-border/80 border border-border"
            : "bg-blue-500 text-white ring-blue-200/80";

    const titleClampClassSession = (s: SessionWithTask) =>
        getDurationSession(s) >= SHORT_TASK_MINUTES ? "line-clamp-2" : "line-clamp-1";

    const titleClampClass = (task: Task) =>
        getDuration(task) >= SHORT_TASK_MINUTES ? "line-clamp-2" : "line-clamp-1";

    const handleBlockKeydown = (event: KeyboardEvent, session: SessionWithTask) => {
        if (event.key === "Enter" || event.key === " ") {
            event.preventDefault();
            const task = getTaskForSession(session);
            if (task) dispatch("select", { task });
        }
    };

    const getCenterPercent = (s: SessionWithTask) => {
        const start = getStartMinutesSession(s);
        const duration = getDurationSession(s);
        return toPercent(start + duration / 2);
    };

    const getMinutesFromClientX = (clientX: number) => {
        if (!trackEl || totalMinutes === 0) return null;
        const rect = trackEl.getBoundingClientRect();
        if (rect.width === 0) return null;
        const x = clientX - rect.left;
        const percent = Math.min(Math.max(x / rect.width, 0), 1);
        const rawMinutes = percent * totalMinutes;
        return clampMinutes(snapMinutes(rawMinutes));
    };

    function getResizeNeighbourBounds(sessionId: number): { prevEnd: number; nextStart: number } {
        const idx = visibleSessions.findIndex((s) => s.id === sessionId);
        if (idx < 0) return { prevEnd: 0, nextStart: totalMinutes };
        const prev = idx > 0 ? visibleSessions[idx - 1] : null;
        const next = idx < visibleSessions.length - 1 ? visibleSessions[idx + 1] : null;
        const prevEnd = prev
            ? getStartMinutesSession(prev) + getDurationSession(prev)
            : 0;
        const nextStart = next ? getStartMinutesSession(next) : totalMinutes;
        return { prevEnd, nextStart };
    }

    function startResize(
        event: Event,
        session: SessionWithTask,
        edge: "start" | "end",
        options: { preventDefault?: boolean } = {},
    ) {
        if (session.status !== "INCOMPLETE") return;
        if (options.preventDefault !== false) {
            event.preventDefault();
        }
        event.stopPropagation();
        if (event instanceof PointerEvent && event.currentTarget instanceof Element) {
            event.currentTarget.setPointerCapture?.(event.pointerId);
        }
        resizingSessionId = session.id;
        resizeEdge = edge;
        const start = getStartMinutesSession(session);
        const duration = Math.max(slotMinutes, getDurationSession(session));
        resizeStartMinutes = start;
        resizeDurationMinutes = duration;
        resizePointerMinutes = null;
    }

    function updateResizePointer(clientX: number) {
        if (!resizingSessionId || !resizeEdge) return;
        const pointerMinutes = getMinutesFromClientX(clientX);
        if (pointerMinutes === null) return;
        resizePointerMinutes = pointerMinutes;
    }

    function handleResizeMove(event: PointerEvent) {
        if (!resizingSessionId || !resizeEdge) return;
        event.preventDefault();
        updateResizePointer(event.clientX);
    }

    function computeResizeRange(
        start: number,
        duration: number,
        pointerMinutes: number,
        edge: "start" | "end",
        excludeSessionId: number | null = null,
    ) {
        const end = start + duration;
        const minDuration = slotMinutes;
        let newStart = start;
        let newEnd = end;
        if (edge === "start") {
            newStart = Math.min(pointerMinutes, end - minDuration);
        } else {
            newEnd = Math.max(pointerMinutes, start + minDuration);
        }
        newStart = clampMinutes(newStart);
        newEnd = clampMinutes(newEnd);
        if (excludeSessionId !== null) {
            const { prevEnd, nextStart } = getResizeNeighbourBounds(excludeSessionId);
            if (edge === "end") {
                newEnd = Math.min(newEnd, nextStart);
            } else {
                newStart = Math.max(newStart, prevEnd);
            }
        }
        if (newEnd - newStart < minDuration) {
            if (edge === "start") {
                newStart = newEnd - minDuration;
            } else {
                newEnd = newStart + minDuration;
            }
        }
        newStart = clampMinutes(newStart);
        newEnd = clampMinutes(newEnd);
        return { start: newStart, end: newEnd, duration: Math.max(minDuration, newEnd - newStart) };
    }

    function handleResizeEnd() {
        if (!resizingSessionId) return;
        const session = visibleSessions.find((s) => s.id === resizingSessionId);
        if (session && resizeStartMinutes !== null && resizeDurationMinutes !== null && resizeEdge) {
            const pointerMinutes =
                resizePointerMinutes ??
                (resizeEdge === "start"
                    ? resizeStartMinutes
                    : resizeStartMinutes + resizeDurationMinutes);
            const next = computeResizeRange(
                resizeStartMinutes,
                resizeDurationMinutes,
                pointerMinutes,
                resizeEdge,
                session.id,
            );
            const startAt = startOfDay(date);
            startAt.setMinutes(startAt.getMinutes() + next.start);
            dispatch("rescheduleSession", {
                session,
                startAt,
                duration: next.duration,
            });
            committedResize = { sessionId: session.id, start: next.start, duration: next.duration };
        }
        resizingSessionId = null;
        resizeEdge = null;
        resizeStartMinutes = null;
        resizeDurationMinutes = null;
        resizePointerMinutes = null;
    }

    $: if (
        committedResize &&
        visibleSessions.some(
            (s) =>
                s.id === committedResize!.sessionId &&
                getStartMinutesSession(s) === committedResize!.start &&
                getDurationSession(s) === committedResize!.duration,
        )
    ) {
        committedResize = null;
    }

    function computePosition(event: CustomEvent<DndEvent<SessionWithTask | Task>>) {
        const dragged = event.detail.info.source?.item as SessionWithTask | Task | undefined;
        if (!dragged || !trackEl || totalMinutes === 0) return null;
        const rect = trackEl.getBoundingClientRect();
        if (rect.width === 0) return null;
        const x = event.detail.info.pointer.clientX - rect.left;
        const percent = Math.min(Math.max(x / rect.width, 0), 1);
        const rawMinutes = percent * totalMinutes;
        const rawDuration =
            "scheduled_start_at" in dragged && "task_id" in dragged
                ? (parseDate(dragged.scheduled_end_at)!.getTime() - parseDate(dragged.scheduled_start_at)!.getTime()) / 60000
                : (dragged as Task).planned_duration ?? defaultDuration;
        const durationSlots = Math.max(1, Math.round(rawDuration / slotMinutes));
        const duration = durationSlots * slotMinutes;
        const maxStart = Math.max(0, totalMinutes - duration);
        const centeredStart = rawMinutes - duration / 2;
        const snappedStart = Math.round(centeredStart / slotMinutes) * slotMinutes;
        const startMinutes = clampMinutes(Math.min(Math.max(snappedStart, 0), maxStart));
        return { startMinutes, duration };
    }

    function handleConsider(event: CustomEvent<DndEvent<Task>>) {
        if (resizingSessionId !== null) return;
        const pos = computePosition(event);
        if (!pos) {
            previewStartMinutes = null;
            previewDuration = null;
            log("consider-none", { reason: "no position" });
            return;
        }
        previewStartMinutes = pos.startMinutes;
        previewDuration = pos.duration;
        log("consider", {
            taskId: event.detail.info.source?.item?.id,
            start: pos.startMinutes,
            duration: pos.duration,
            pointerX: event.detail.info.pointer.clientX,
        });
    }

    function handleFinalize(event: CustomEvent<DndEvent<SessionWithTask | Task>>) {
        if (resizingSessionId !== null) return;
        const dragged = event.detail.info.source?.item as SessionWithTask | Task | undefined;
        const pos = computePosition(event);
        previewStartMinutes = null;
        previewDuration = null;
        if (!dragged || !pos) {
            log("finalize-skipped", { hasDragged: Boolean(dragged), hasPos: Boolean(pos) });
            return;
        }
        if ("task_id" in dragged && "task_title" in dragged) {
            const session = dragged as SessionWithTask;
            const startAt = startOfDay(date);
            startAt.setMinutes(startAt.getMinutes() + pos.startMinutes);
            dispatch("rescheduleSession", { session, startAt, duration: pos.duration });
            return;
        }
        const task = dragged as Task;
        const startAt = startOfDay(date);
        startAt.setMinutes(startAt.getMinutes() + pos.startMinutes);
        log("finalize", { taskId: task.id, startMinutes: pos.startMinutes, duration: pos.duration });
        dispatch("schedule", { taskId: Number(task.id), startAt });
    }
</script>

<svelte:window
    on:pointermove|capture={handleResizeMove}
    on:pointerup|capture={handleResizeEnd}
    on:pointercancel|capture={handleResizeEnd}
/>

<section class="flex flex-col border border-border rounded-2xl bg-surface shadow-sm p-6 gap-4">
    <header class="flex items-center justify-between">
        <div>
            <p class="text-xs uppercase text-gray-500 tracking-wide">Schedule</p>
            <h3 class="text-lg font-semibold text-gray-800">
                {date.toLocaleDateString(undefined, { weekday: "long", month: "short", day: "numeric" })}
            </h3>
        </div>
        <div class="flex items-center gap-2">
            <button
                class="inline-flex items-center justify-center w-8 h-8 text-gray-600 hover:bg-blue-600 hover:text-white rounded-lg border border-border"
                aria-label="Previous day"
                on:click={decrementDate}
            >
                ‹
            </button>
            <button
                class="inline-flex items-center justify-center w-8 h-8 text-gray-600 hover:bg-blue-600 hover:text-white rounded-lg border border-border"
                aria-label="Next day"
                on:click={incrementDate}
            >
                ›
            </button>
        </div>
    </header>

    <div class="sm:px-6">
        <!-- Desktop horizontal timeline -->
        <div class="hidden md:block">
            <div
                class="relative h-36 border border-dashed border-border rounded-xl bg-surface overflow-visible"
                use:dndzone={zoneOptions}
                bind:this={trackEl}
                on:consider={handleConsider}
                on:finalize={handleFinalize}
                on:dragleave={() => {
                    previewStartMinutes = null;
                    previewDuration = null;
                    log("dragleave", {});
                }}
                role="region"
                aria-label="Schedule timeline"
            >
                <div class="relative w-full h-full">
                    <!-- Tick marks -->
                    {#if totalMinutes > 0}
                        {#each ticks as t}
                            <div
                                class="absolute top-0 bottom-0 border-l pointer-events-none"
                                style={`left:${toPercent((t * slotMinutes))}%; border-color: ${
                                    t * slotMinutes % 60 === 0 ? "#CBD5E1" : "#E2E8F0"
                                };`}
                            ></div>
                        {/each}
                    {/if}

                    {#if nowLineMinutes !== null}
                        <div
                            class="absolute top-0 bottom-0 pointer-events-none"
                            style={`left:${toPercent(nowLineMinutes)}%; z-index:10;`}
                        >
                            <div class="absolute inset-y-0 w-[2px] bg-red-500 opacity-80"></div>
                        </div>
                    {/if}

                    <!-- Scheduled blocks (sessions) -->
                    {#each visibleSessions as session (session.id)}
                        {#if isShortSession(session) && shortTaskLaneMap.has(session.id)}
                            {#key session.id}
                                {@const lane = Number(shortTaskLaneMap.get(session.id))}
                                {@const labelOffset = SHORT_LABEL_BASE_OFFSET + (SHORT_LABEL_LANES - lane) * SHORT_LABEL_VERTICAL_GAP}
                                {@const lineLength = Math.max(0, labelOffset - SHORT_LABEL_TEXT_HEIGHT - SHORT_LABEL_LINE_GAP)}
                                {@const displayStart = resizingSessionId === session.id && resizePreview ? resizePreview.start : (committedResize?.sessionId === session.id ? committedResize.start : getStartMinutesSession(session))}
                                {@const displayDuration = resizingSessionId === session.id && resizePreview ? resizePreview.duration : (committedResize?.sessionId === session.id ? committedResize.duration : getDurationSession(session))}
                                <div
                                    class="absolute pointer-events-none z-30"
                                    style={`left:${toPercent(displayStart)}%; width:${toPercent(displayDuration)}%; top:${BAR_TOP_PERCENT}%;`}
                                >
                                    <div
                                        class="absolute left-1/2 -translate-x-1/2 bg-gray-600"
                                        style={`width:1px; height:${lineLength}px; top:-${lineLength}px;`}
                                    ></div>
                                    <div
                                        class="absolute text-[11px] font-medium text-gray-600 max-w-[180px] whitespace-nowrap overflow-hidden text-ellipsis text-left"
                                        style={`transform:translateY(-${labelOffset}px); left:0;`}
                                    >
                                        {session.task_title}
                                    </div>
                                </div>
                            {/key}
                        {/if}

                        {@const blockStart = resizingSessionId === session.id && resizePreview ? resizePreview.start : (committedResize?.sessionId === session.id ? committedResize.start : getStartMinutesSession(session))}
                        {@const blockDuration = resizingSessionId === session.id && resizePreview ? resizePreview.duration : (committedResize?.sessionId === session.id ? committedResize.duration : getDurationSession(session))}
                        <div
                            class={`absolute ${session.status === "INCOMPLETE" ? "cursor-grab" : "cursor-default"}`}
                            style={`left:${toPercent(blockStart)}%; width:${toPercent(blockDuration)}%; top:${BAR_TOP_PERCENT}%; height:${BAR_HEIGHT_PERCENT}%; z-index:${session.status === "INCOMPLETE" ? 20 : 5};`}
                            draggable={session.status === "INCOMPLETE" && !isResizing}
                            data-dnd-id={session.id}
                            role="group"
                            aria-label={session.task_title}
                        >
                            {#if session.status === "INCOMPLETE"}
                                <button
                                    type="button"
                                    class="absolute inset-y-0 left-0 w-2 cursor-ew-resize z-20 rounded-l-lg hover:bg-white/20 focus:outline-none"
                                    aria-label="Resize session start"
                                    tabindex="-1"
                                    on:pointerdown|preventDefault|stopPropagation={(e) => startResize(e, session, "start")}
                                ></button>
                                <button
                                    type="button"
                                    class="absolute inset-y-0 right-0 w-2 cursor-ew-resize z-20 rounded-r-lg hover:bg-white/20 focus:outline-none"
                                    aria-label="Resize session end"
                                    tabindex="-1"
                                    on:pointerdown|preventDefault|stopPropagation={(e) => startResize(e, session, "end")}
                                ></button>
                            {/if}
                            {#if isShortSession(session)}
                                <button
                                    type="button"
                                    class={`h-full w-full rounded-lg shadow-lg ring-1 relative text-left border-0 cursor-inherit focus:ring-2 focus:ring-blue-500/50 focus:ring-inset ${blockToneSession(session)} ${session.status === "COMPLETED" ? "opacity-80" : ""}`}
                                    aria-label={session.task_title}
                                    on:click={() => {
                                        const task = getTaskForSession(session);
                                        if (task) dispatch("select", { task });
                                    }}
                                    on:keydown={(e) => handleBlockKeydown(e, session)}
                                >
                                    <span class="sr-only">{session.task_title}</span>
                                </button>
                            {:else}
                                <button
                                    type="button"
                                    class={`h-full w-full rounded-lg shadow-lg ring-1 px-3 py-2 flex flex-col justify-between relative text-left border-0 cursor-inherit focus:ring-2 focus:ring-blue-500/50 focus:ring-inset ${blockToneSession(session)} ${session.status === "COMPLETED" ? "opacity-80" : ""}`}
                                    on:click={() => {
                                        const task = getTaskForSession(session);
                                        if (task) dispatch("select", { task });
                                    }}
                                    on:keydown={(e) => handleBlockKeydown(e, session)}
                                >
                                    <div class={`font-semibold text-[13px] leading-tight ${titleClampClassSession(session)}`}>
                                        {session.task_title}
                                    </div>
                                    <div class="flex items-center justify-between gap-2">
                                        <div class="text-[11px] opacity-90 leading-tight">{formatTimeRangeSession(session)}</div>
                                    </div>
                                </button>
                            {/if}
                        </div>
                    {/each}

                    <!-- Preview block while dragging -->
                    {#if previewStartMinutes !== null && previewDuration !== null && resizingSessionId === null}
                        <div
                            class="absolute pointer-events-none"
                            style={`left:${toPercent(previewStartMinutes)}%; width:${toPercent(previewDuration)}%; top:${BAR_TOP_PERCENT}%; height:${BAR_HEIGHT_PERCENT}%;`}
                        >
                            <div class="h-full rounded-lg border-2 border-blue-400 bg-blue-100/70 text-blue-800 px-3 py-2 flex flex-col justify-between shadow-md">
                                <div class="font-semibold text-[13px] leading-tight line-clamp-1">Drop to schedule</div>
                                <div class="text-[11px] opacity-80 leading-tight">
                                    {#if previewStartMinutes !== null}
                                        {#if previewDuration !== null}
                                            {#if totalMinutes > 0}
                                                {#if previewDuration >= 0}
                                                    {#if previewStartMinutes >= 0}
                                                        {#if previewStartMinutes + previewDuration <= totalMinutes}
                                                            {new Date(startOfDay(date).getTime() + previewStartMinutes * 60000).toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" })}
                                                            —
                                                            {new Date(startOfDay(date).getTime() + (previewStartMinutes + previewDuration) * 60000).toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" })}
                                                        {/if}
                                                    {/if}
                                                {/if}
                                            {/if}
                                        {/if}
                                    {/if}
                                </div>
                            </div>
                        </div>
                    {/if}
                </div>

                <div class="absolute inset-0 pointer-events-none rounded-xl ring-1 ring-inset ring-transparent"></div>
            </div>

            <div class="relative h-6 text-[11px] text-gray-600 px-8">
                {#if totalMinutes > 0}
                    {#each ticks as t}
                        {#if t * slotMinutes % 60 === 0}
                            <span
                                class="absolute -translate-x-1/2"
                                style={`left:${toPercent((t * slotMinutes))}%;`}
                            >
                                {formatHourLabel(t)}
                            </span>
                        {/if}
                    {/each}
                {/if}
            </div>
        </div>

        <!-- Mobile vertical timeline -->
        <div class="block md:hidden w-full">
            {#if visibleSessions.length === 0}
                <p class="text-sm text-gray-500">Nothing scheduled for this day.</p>
            {:else}
                <div class="space-y-2">
                    <div class="flex flex-col gap-1.5">
                        {#each visibleSessions as session (session.id)}
                            {@const task = getTaskForSession(session)}
                            <div class="flex w-full items-start gap-2 rounded-lg px-0.5 py-1.5 transition hover:bg-blue-50/60">
                                <button
                                    type="button"
                                    class="flex flex-1 min-w-0 items-start gap-2 text-left"
                                    on:click={() => task && dispatch("select", { task })}
                                >
                                    <span
                                        class={`mt-1 h-3 w-3 flex-shrink-0 rounded-full ${session.status === "COMPLETED" ? "bg-gray-400" : "bg-blue-500"}`}
                                    ></span>
                                    <div class="min-w-0 flex-1 space-y-0.5">
                                        <p class="text-sm font-semibold text-gray-900 leading-tight truncate">{session.task_title}</p>
                                        <p class="text-xs text-gray-500 leading-tight">{formatTimeRangeSession(session)}</p>
                                    </div>
                                    <span
                                        class={`ml-2 flex-shrink-0 text-[11px] font-semibold whitespace-nowrap ${
                                            session.status === "COMPLETED" ? "text-gray-600" : "text-blue-600"
                                        }`}
                                    >
                                        {sessionStatusLabel(session)}
                                    </span>
                                </button>
                            </div>
                        {/each}
                    </div>
                </div>
            {/if}
        </div>

    {#if DEBUG}
        <div class="text-[11px] text-gray-500 italic">Debug: {debugMessage}</div>
    {/if}
    </div>
</section>
