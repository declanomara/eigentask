<script lang="ts">
  import TaskCard from "../../TaskCard.svelte";
  export let data: { tasks: Array<{ id: number; title: string; description?: string | null }> };
  import { env as publicEnv } from '$env/dynamic/public';

  // Build-time public envs. Provide sensible fallbacks for dev.
  const API_URL = publicEnv.PUBLIC_API_ORIGIN || 'http://localhost:8000';
  const appOrigin = publicEnv.PUBLIC_APP_ORIGIN || (typeof window !== 'undefined' ? window.location.origin : 'http://localhost:5173');
  const logoutUrl = `${API_URL}/auth/logout?return_to=${encodeURIComponent(appOrigin + '/')}`;
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
