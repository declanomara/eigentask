<script lang="ts">
  export let id: string | undefined = undefined;
  export let type: string = "text";
  export let name: string | undefined = undefined;
  export let value: string | number | null = "";
  export let placeholder: string = "";
  export let required: boolean = false;
  export let min: string | number | undefined = undefined;
  export let max: string | number | undefined = undefined;
  export let step: string | number | undefined = undefined;
  export let className: string = "";

  const inputClass =
    "border border-border rounded-lg px-3 py-2.5 text-sm w-full focus:outline-none focus:ring-2 focus:ring-blue-500/20 focus:border-border-strong";
</script>

<input
  {id}
  {type}
  {name}
  {placeholder}
  {required}
  {min}
  {max}
  {step}
  class="{inputClass} {className}"
  bind:value
/>
