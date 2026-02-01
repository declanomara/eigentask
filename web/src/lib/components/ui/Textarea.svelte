<script lang="ts">
  export let id: string | undefined = undefined;
  export let name: string | undefined = undefined;
  export let value: string = "";
  export let placeholder: string = "";
  export let rows: number = 3;
  export let className: string = "";

  const textareaClass =
    "border border-border rounded-lg px-3 py-2.5 text-sm w-full focus:outline-none focus:ring-2 focus:ring-blue-500/20 focus:border-border-strong resize-y";
</script>

<textarea
  {id}
  {name}
  {placeholder}
  {rows}
  class="{textareaClass} {className}"
  bind:value
></textarea>
