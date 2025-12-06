<script lang="ts">
  import OverlayShell from "$lib/components/ui/OverlayShell.svelte";
  import { createEventDispatcher } from "svelte";
  export let open = false;
  export let title = "";

  const dispatch = createEventDispatcher();

  function close() {
    dispatch("close");
  }
</script>

<OverlayShell {open} {title} on:close={close}>
  <slot />
</OverlayShell>
