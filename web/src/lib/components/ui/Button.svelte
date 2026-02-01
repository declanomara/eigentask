<script lang="ts">
  import { createEventDispatcher } from "svelte";

  export let type: "button" | "submit" | "reset" = "button";
  export let variant: "primary" | "secondary" | "danger" = "primary";
  export let disabled: boolean = false;
  /** When true and variant is danger, use filled style (e.g. "Confirm delete") */
  export let confirming: boolean = false;
  export let className: string = "";

  const dispatch = createEventDispatcher<{ click: MouseEvent }>();

  function handleClick(event: MouseEvent) {
    dispatch("click", event);
  }

  const baseClass =
    "rounded-lg px-4 py-2 text-sm font-medium focus:outline-none focus:ring-2 focus:ring-blue-500/30 disabled:opacity-60 disabled:pointer-events-none";
  $: variantClass =
    variant === "primary"
      ? "bg-blue-600 text-white hover:bg-blue-700"
      : variant === "secondary"
        ? "border border-border text-gray-700 hover:bg-surface-hover"
        : confirming
          ? "bg-rose-600 text-white border-rose-600 hover:bg-rose-700 focus:ring-rose-500/30"
          : "border border-rose-300 text-rose-700 hover:bg-rose-50 focus:ring-rose-500/30";
</script>

<button
  {...$$restProps}
  {type}
  {disabled}
  class="{baseClass} {variantClass} {className}"
  on:click={handleClick}
>
  <slot />
</button>
