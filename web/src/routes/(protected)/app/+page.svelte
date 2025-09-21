<script lang="ts">
  import TaskCard from "../../TaskCard.svelte";
  export let data: { tasks: Array<{ id: number; title: string; description?: string | null }> };

  const API_URL = 'http://localhost:8000';
  const logoutUrl = `${API_URL}/auth/logout?return_to=${encodeURIComponent('http://localhost:5173/')}`;
</script>

<div style="margin: 1rem 0; display: flex; gap: 0.5rem;">
  <a href={logoutUrl}><button>Logout</button></a>
  <a href="/settings"><button>Settings</button></a>
</div>

{#if data?.tasks?.length}
  <div>
    {#each data.tasks as t}
      <TaskCard id={t.id} title={t.title} description={t.description} />
    {/each}
  </div>
{:else}
  <p>No tasks yet.</p>
{/if}
