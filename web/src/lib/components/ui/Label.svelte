<script lang="ts">
  export let forId: string | undefined = undefined;
  export let className: string = "";
</script>

<label
  for={forId}
  class="text-sm font-medium text-gray-800 {className}"
>
  <slot />
</label>
