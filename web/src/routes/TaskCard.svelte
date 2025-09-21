<script lang="ts">
    let { id, title, description } = $props()
</script>

<div class="task-card">
    <h4>{id}</h4>
    <h2>{title}</h2>
    {#if description}
        <p>{description}</p>
    {/if}
</div>

<style>
    .task-card {
        border: 1px solid #ccc;
        padding: 10px;
        margin: 10px;
    }
</style>