<script lang="ts">
    import { createEventDispatcher, onMount } from "svelte";
    export let open = false;
    export let title = "";

    const dispatch = createEventDispatcher();
    let dialogEl: HTMLElement | null = null;

    function close() {
        dispatch("close");
    }

    function onBackdropKeydown(e: KeyboardEvent) {
        if (e.key === "Escape" || e.key === "Enter" || e.key === " ") {
            e.preventDefault();
            close();
        }
    }

    function onBackdropClick(e: MouseEvent) {
        if (e.target === e.currentTarget) close();
    }

    onMount(() => {
        if (open) {
            // focus the first focusable element inside the modal
            const first = dialogEl?.querySelector(
                'input,textarea,button,select, [tabindex]:not([tabindex="-1"])',
            );
            (first as HTMLElement | null)?.focus();
        }
    });
</script>

{#if open}
    <div
        class="fixed inset-0 bg-black/50 z-50"
        on:click={onBackdropClick}
        on:keydown={onBackdropKeydown}
        role="button"
        tabindex="0"
        aria-label="Modal backdrop"
    ></div>
    <div
        class="fixed inset-0 flex items-center justify-center z-50"
        role="dialog"
        aria-modal="true"
        aria-label={title}
    >
        <div
            class="bg-white rounded-md shadow-lg w-full max-w-md mx-4 p-4"
            bind:this={dialogEl}
            role="document"
        >
            <div class="flex items-center justify-between mb-2">
                <h3 class="text-lg font-semibold">{title}</h3>
                <button
                    aria-label="Close"
                    class="text-gray-500"
                    on:click={close}>✕</button
                >
            </div>
            <slot />
        </div>
    </div>
{/if}
