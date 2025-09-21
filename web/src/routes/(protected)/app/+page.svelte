<script lang="ts">
  import TaskCard from "../../TaskCard.svelte";
  export let data: { tasks: Array<{ id: number; title: string; description?: string | null }>; error?: string };
  import { env as publicEnv } from '$env/dynamic/public';

  // Build-time public envs. Provide sensible fallbacks for dev.
  const API_URL = publicEnv.PUBLIC_API_ORIGIN || 'http://localhost:8000';
  const appOrigin = publicEnv.PUBLIC_APP_ORIGIN || (typeof window !== 'undefined' ? window.location.origin : 'http://localhost:5173');
  const logoutUrl = `${API_URL}/auth/logout?return_to=${encodeURIComponent(appOrigin + '/')}`;

  let showCreate = false;
</script>

<div style="margin: 1rem 0; display: flex; gap: 0.5rem;">
  <a href={logoutUrl}><button>Logout</button></a>
  <a href="/settings"><button>Settings</button></a>
  <button on:click={() => showCreate = !showCreate} title="Create task" aria-label="Create task">+ New</button>
</div>

{#if data?.error}
  <p style="color: crimson;">Error loading tasks: {data.error}</p>
{/if}

{#if showCreate}
  <form method="POST" action="?/create" style="margin: 1rem 0; display: grid; gap: 0.5rem; max-width: 480px;">
    <input name="title" placeholder="Task title" required />
    <textarea name="description" placeholder="Description (optional)" rows="3"></textarea>
    <div style="display:flex; gap: .5rem;">
      <button type="submit">Create</button>
      <button type="button" on:click={() => showCreate = false}>Cancel</button>
    </div>
  </form>
{/if}

{#if data?.tasks?.length}
  <div>
    {#each data.tasks as t}
      <div style="display:flex; align-items:flex-start; gap:.5rem; margin-bottom: .75rem;">
        <TaskCard id={t.id} title={t.title} description={t.description} />
        <form method="POST" action="?/delete" style="margin: 0;">
          <input type="hidden" name="id" value={t.id} />
          <button type="submit" title="Delete task" aria-label="Delete task" style="background: transparent; border: 1px solid #ddd; padding: .25rem .5rem; cursor: pointer;">🗑️</button>
        </form>
      </div>
    {/each}
  </div>
{:else}
  <p>No tasks yet.</p>
{/if}
