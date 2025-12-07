<script lang="ts">
    import { createEventDispatcher } from "svelte";
    import { dndzone, type DndEvent, type DndZoneOptions } from "svelte-dnd-action";
    import type { Task } from "$lib/apiClient";

    export let startHour = 8;
    export let endHour = 20;
    export let slotMinutes = 15;
    export let date: Date = new Date();
    export let tasks: Task[] = [];
    export let defaultDuration = 60;

    const dispatch = createEventDispatcher<{
        schedule: { taskId: number; startAt: Date };
        select: { task: Task };
    }>();

    const DEBUG = true;

    let trackEl: HTMLDivElement | null = null;
    let previewStartMinutes: number | null = null;
    let previewDuration: number | null = null;
    let ticks: number[] = [];
    let visibleTasks: Task[] = [];
    let debugMessage = "";

    $: totalMinutes = Math.max(0, (endHour - startHour) * 60);
    $: hours = Math.max(0, endHour - startHour);
    $: ticks = Array.from({ length: Math.floor((hours * 60) / slotMinutes) + 1 }, (_, i) => i as number);
    const statusRank = (task: Task) => (task.status === "PLANNED" ? 0 : task.status === "COMPLETED" ? 1 : 2);
    const startMillis = (task: Task) => {
        if (!task.planned_start_at) return 0;
        const d = new Date(task.planned_start_at);
        return d.getTime();
    };
    $: visibleTasks = tasks
        .filter(
            (task) =>
                (task.status === "PLANNED" || task.status === "COMPLETED") &&
                isSameDay(task.planned_start_at, date),
        )
        .sort((a, b) => {
            const statusDiff = statusRank(a) - statusRank(b);
            if (statusDiff !== 0) return statusDiff;
            return startMillis(a) - startMillis(b);
        });

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
        items: visibleTasks,
    } satisfies DndZoneOptions<Task>;

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

    const getStartMinutes = (task: Task) => {
        if (!task.planned_start_at) return 0;
        const start = parseDate(task.planned_start_at);
        if (!start) return 0;
        return clampMinutes((start.getHours() - startHour) * 60 + start.getMinutes());
    };

    const getDuration = (task: Task) => {
        const start = parseDate(task.planned_start_at);
        const end = parseDate(task.planned_end_at);
        if (start && end) {
            return clampMinutes(Math.max(0, (end.getTime() - start.getTime()) / 60000));
        }
        return clampMinutes(task.planned_duration ?? defaultDuration);
    };

    const formatTimeRange = (task: Task) => {
        const start = parseDate(task.planned_start_at);
        const end =
            parseDate(task.planned_end_at) ??
            (start ? new Date(start.getTime() + getDuration(task) * 60000) : null);

        if (!start || !end) return "";
        const startLabel = start.toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" });
        const endLabel = end.toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" });
        return `${startLabel} — ${endLabel}`;
    };

    const taskStatusLabel = (task: Task) => (task.status === "COMPLETED" ? "Completed" : "Scheduled");

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

    const blockTone = (task: Task) =>
        task.status === "COMPLETED"
            ? "bg-gray-300 text-gray-800 ring-gray-200/80 border border-gray-200"
            : "bg-blue-500 text-white ring-blue-200/80";

    function computePosition(event: CustomEvent<DndEvent<Task>>) {
        const dragged = event.detail.info.source?.item as Task | undefined;
        if (!dragged || !trackEl || totalMinutes === 0) return null;
        const rect = trackEl.getBoundingClientRect();
        if (rect.width === 0) return null;
        const x = event.detail.info.pointer.clientX - rect.left;
        const percent = Math.min(Math.max(x / rect.width, 0), 1);
        const rawMinutes = percent * totalMinutes;
        const rawDuration = dragged.planned_duration ?? defaultDuration;
        // Snap duration to slot size to keep start/end on 00/15/30/45.
        const durationSlots = Math.max(1, Math.round(rawDuration / slotMinutes));
        const duration = durationSlots * slotMinutes;
        const maxStart = Math.max(0, totalMinutes - duration);
        // Center the block on the cursor, then snap the start to the slot grid.
        const centeredStart = rawMinutes - duration / 2;
        const snappedStart = Math.round(centeredStart / slotMinutes) * slotMinutes;
        const startMinutes = clampMinutes(Math.min(Math.max(snappedStart, 0), maxStart));
        return { startMinutes, duration };
    }

    function handleConsider(event: CustomEvent<DndEvent<Task>>) {
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

    function handleFinalize(event: CustomEvent<DndEvent<Task>>) {
        const dragged = event.detail.info.source?.item as Task | undefined;
        const pos = computePosition(event);
        previewStartMinutes = null;
        previewDuration = null;
        if (!dragged || !pos) {
            log("finalize-skipped", {
                hasDragged: Boolean(dragged),
                hasPos: Boolean(pos),
            });
            return;
        }
        const startAt = startOfDay(date);
        startAt.setMinutes(startAt.getMinutes() + pos.startMinutes);
        log("finalize", {
            taskId: dragged.id,
            startMinutes: pos.startMinutes,
            duration: pos.duration,
            startAt: startAt.toISOString(),
        });
        dispatch("schedule", { taskId: Number(dragged.id), startAt });
    }
</script>

<section class="flex flex-col border border-gray-200 rounded-2xl bg-white shadow-sm p-6 gap-4">
    <header class="flex items-center justify-between">
        <div>
            <p class="text-xs uppercase text-gray-500 tracking-wide">Schedule</p>
            <h3 class="text-lg font-semibold text-gray-800">
                {date.toLocaleDateString(undefined, { weekday: "long", month: "short", day: "numeric" })}
            </h3>
        </div>
        <div class="flex items-center gap-2">
            <button
                class="inline-flex items-center justify-center w-8 h-8 text-gray-600 hover:bg-blue-600 hover:text-white rounded-lg border border-gray-200"
                aria-label="Previous day"
                on:click={decrementDate}
            >
                ‹
            </button>
            <button
                class="inline-flex items-center justify-center w-8 h-8 text-gray-600 hover:bg-blue-600 hover:text-white rounded-lg border border-gray-200"
                aria-label="Next day"
                on:click={incrementDate}
            >
                ›
            </button>
        </div>
    </header>

    <div class="md:px-6">
        <!-- Desktop horizontal timeline -->
        <div class="hidden md:block">
            <div
                class="relative h-36 border border-dashed border-gray-300 rounded-xl bg-gray-50 overflow-hidden"
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

                    <!-- Scheduled blocks -->
                    {#each visibleTasks as task (task.id)}
                        {#if task.planned_start_at}
                            <div
                                class={`absolute ${task.status === "PLANNED" ? "cursor-grab" : "cursor-default"}`}
                                style={`left:${toPercent(getStartMinutes(task))}%; width:${toPercent(getDuration(task))}%; top:10%; height:80%; z-index:${task.status === "PLANNED" ? 20 : 5};`}
                                draggable={task.status === "PLANNED"}
                                data-dnd-id={task.id}
                                on:click={() => dispatch("select", { task })}
                            >
                                <div
                                    class={`h-full rounded-lg shadow-lg ring-1 px-3 py-2 flex flex-col justify-between ${blockTone(task)} ${task.status === "COMPLETED" ? "opacity-80" : ""}`}
                                >
                                    <div class="font-semibold text-[13px] leading-tight line-clamp-1">{task.title}</div>
                                    <div class="text-[11px] opacity-90 leading-tight">{formatTimeRange(task)}</div>
                                </div>
                            </div>
                        {/if}
                    {/each}

                    <!-- Preview block while dragging -->
                    {#if previewStartMinutes !== null && previewDuration !== null}
                        <div
                            class="absolute pointer-events-none"
                            style={`left:${toPercent(previewStartMinutes)}%; width:${toPercent(previewDuration)}%; top:10%; height:80%;`}
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
            <div class="space-y-2">
                {#if visibleTasks.length === 0}
                    <div class="rounded-xl border border-gray-200 bg-gray-50 px-3 py-3 text-sm text-gray-600 shadow-sm">
                        Nothing scheduled for this day.
                    </div>
                {:else}
                    <div class="flex flex-col gap-1.5">
                        {#each visibleTasks as task (task.id)}
                            <button
                                type="button"
                                class="flex w-full items-start gap-2 rounded-lg px-0.5 py-1.5 text-left transition hover:bg-blue-50/60"
                                on:click={() => dispatch("select", { task })}
                            >
                                <span
                                    class={`mt-1 h-3 w-3 rounded-full ${task.status === "COMPLETED" ? "bg-gray-400" : "bg-blue-500"}`}
                                ></span>
                                <div class="flex-1 min-w-0 space-y-0.5">
                                    <p class="text-sm font-semibold text-gray-900 leading-tight truncate">{task.title}</p>
                                    <p class="text-xs text-gray-500 leading-tight">{formatTimeRange(task)}</p>
                                </div>
                                <span
                                    class={`ml-2 text-[11px] font-semibold whitespace-nowrap ${
                                        task.status === "COMPLETED" ? "text-gray-600" : "text-blue-600"
                                    }`}
                                >
                                    {taskStatusLabel(task)}
                                </span>
                            </button>
                        {/each}
                    </div>
                    <div class="flex items-center justify-between text-xs text-gray-600 pt-1">
                        <div class="flex items-center gap-2">
                            <span class="h-2 w-2 rounded-full bg-blue-500"></span>
                            Scheduled
                        </div>
                        <div class="flex items-center gap-2">
                            <span class="h-2 w-2 rounded-full bg-gray-400"></span>
                            Completed
                        </div>
                    </div>
                {/if}
            </div>
        </div>

    {#if DEBUG}
        <div class="text-[11px] text-gray-500 italic">Debug: {debugMessage}</div>
    {/if}
</section>
