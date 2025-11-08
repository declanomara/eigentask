<script lang="ts">
    // Configurable daily timeline
    export let startHour: number = 8;
    export let endHour: number = 17;
    export let date: Date = new Date();

    function incrementDate() {
        date = new Date(date);
        date.setDate(date.getDate() + 1);
    }

    function decrementDate() {
        date = new Date(date);
        date.setDate(date.getDate() - 1);
    }

    // Derived values
    // total ticks = (end - start) * 4 (4 slots per hour for 15-min steps)
    $: hours = Math.max(0, endHour - startHour);
    $: totalTicks = hours * 4;
    $: ticks = Array.from({ length: totalTicks + 1 }, (_, i) => i);

    // Helpers
    const formatHourLabel = (hour: number) => {
        const h = ((hour + 24) % 24).toString().padStart(2, "0");
        return `${h}:00`;
    };
</script>

<div
    class="flex flex-col border border-gray-300 rounded-xl bg-gray-50 min-h-[20vh] p-2 m-2"
>
    <!-- Timeline track with hourly/minor ticks -->
    <!-- <div
        class="relative border border-gray-300 rounded-xl bg-gray-100 h-full p-2 m-2"
    >
        {#if totalTicks > 0}
            {#each ticks as t}
                <div
                    style="
               position: absolute;
               left: {(t / totalTicks) * 100}%;
               top: 0;
               bottom: 0;
               width: 1px;
               background: {t % 4 === 0 ? '#333' : '#bbb'};
               height: {t % 4 === 0 ? '12px' : '6px'};
             "
                    aria-hidden="true"
                />
            {/each}
        {/if}
    </div> -->
    <div
        class="relative border border-gray-300 rounded-sm bg-gray-100 h-full p-2 m-2"
    >
        {#if totalTicks > 0}
            {#each ticks as t}
                <div
                    class="absolute bottom-0 w-px"
                    style="left: {(t / totalTicks) * 100}%;"
                    class:bg-gray-800={t % 4 === 0}
                    class:bg-gray-400={t % 4 !== 0}
                    class:h-[12px]={t % 4 === 0}
                    class:h-[6px]={t % 4 !== 0}
                    aria-hidden="true"
                ></div>
            {/each}
        {/if}
    </div>

    <!-- Hour labels underneath the major ticks (every 4 steps) -->
    <div class="relative h-10 p-2 mx-4">
        {#each ticks as t}
            {#if t % 4 === 0}
                <span
                    style="
               position: absolute;
               left: {(t / totalTicks) * 100}%;
               transform: translateX(-50%);
               bottom: 0;
               font-size: 12px;
               color: #333;
             "
                >
                    {startHour + Math.floor(t / 4)}:00
                </span>
            {/if}
        {/each}
    </div>

    <!-- Timeline -->
    <!-- <div
        class="border border-gray-300 rounded-xl bg-gray-100 h-full p-2 m-2"
    ></div> -->

    <!--Timeline controls -->
    <div class="flex ml-auto mt-auto items-center">
        <button
            class="inline-flex items-center justify-center w-8 h-8 text-gray-600 hover:bg-blue-600 hover:text-white rounded-xl mx-2"
            aria-label="Previous"
            on:click={decrementDate}
        >
            <svg
                width="16"
                height="16"
                viewBox="0 0 24 24"
                fill="none"
                stroke="currentColor"
                stroke-width="2"
                aria-hidden="true"
            >
                <path d="M15 18l-6-6 6-6" />
            </svg>
        </button>
        <span class="text-gray-600">{date.toLocaleDateString()}</span>
        <button
            class="inline-flex items-center justify-center w-8 h-8 text-gray-600 hover:bg-blue-600 hover:text-white rounded-xl mx-2"
            aria-label="Next"
            on:click={incrementDate}
        >
            <svg
                width="16"
                height="16"
                viewBox="0 0 24 24"
                fill="none"
                stroke="currentColor"
                stroke-width="2"
                aria-hidden="true"
            >
                <path d="M9 18l6-6-6-6" />
            </svg>
        </button>
    </div>
</div>
