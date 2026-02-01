<script lang="ts">
  import { createEventDispatcher, tick } from "svelte";

  export let open = false;
  export let title = "";
  export let align: "center" | "right" = "center";
  export let widthClass = "max-w-md";
  export let panelClass = "";
  export let closeOnBackdrop = true;
  export let closeOnEscape = true;

  const dispatch = createEventDispatcher<{ close: void }>();
  let panelEl: HTMLElement | null = null;

  function close() {
    dispatch("close");
  }

  function handleBackdropClick(event: MouseEvent) {
    if (!closeOnBackdrop) return;
    if (event.target === event.currentTarget) {
      close();
    }
  }

  function handleBackdropKeydown(event: KeyboardEvent) {
    if (!closeOnBackdrop) return;
    if (event.key === "Enter" || event.key === " " || event.key === "Escape") {
      event.preventDefault();
      close();
    }
  }

  function handleKeydown(event: KeyboardEvent) {
    if (!open || !closeOnEscape) return;
    if (event.key === "Escape") {
      event.preventDefault();
      close();
    }
  }

  $: if (open) {
    // Focus the first focusable element inside the panel when opened.
    tick().then(() => {
      const first = panelEl?.querySelector(
        'input,textarea,button,select,[tabindex]:not([tabindex="-1"])',
      ) as HTMLElement | null;
      first?.focus();
    });
  }
</script>

<svelte:window on:keydown={handleKeydown} />

{#if open}
  <div
    class="fixed inset-0 bg-black/50 z-50"
    role="button"
    tabindex="0"
    aria-label="Modal backdrop"
    on:click={handleBackdropClick}
    on:keydown={handleBackdropKeydown}
  ></div>
  <div
    class={`fixed inset-0 z-50 flex ${align === "center" ? "items-center justify-center" : "items-stretch justify-end"}`}
    role="dialog"
    aria-modal="true"
    aria-label={title}
  >
    <div
      class={`bg-surface-elevated shadow-lg w-full ${align === "center" ? "mx-4 my-8 rounded-xl" : "h-full max-w-md md:max-w-lg rounded-none md:rounded-l-xl flex flex-col overflow-hidden"} ${widthClass} ${panelClass}`}
      bind:this={panelEl}
      role="document"
    >
      <slot name="header" {close}>
        <div class="flex items-center justify-between px-4 py-3 border-b border-border-muted flex-shrink-0">
          <h3 class="text-lg font-semibold text-gray-800">{title}</h3>
          <button
            aria-label="Close"
            class="text-gray-500 hover:text-gray-700 focus:outline-none focus:ring-2 focus:ring-blue-500/30 rounded"
            on:click={close}
            type="button"
          >
            ✕
          </button>
        </div>
      </slot>
      <div class={align === "right" ? "flex-1 min-h-0 overflow-y-auto flex flex-col p-4" : "p-4"}>
        <slot {close} />
      </div>
    </div>
  </div>
{/if}
