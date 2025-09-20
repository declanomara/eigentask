<script lang="ts">
    let {isAuthenticated, onLogin, onLogout} = $props();
</script>

{#if isAuthenticated}
    <p>You are logged in.</p>
    <button onclick={onLogout}>Log out</button>
{:else}
    <p>You are not logged in.</p>
    <button onclick={onLogin}>Log in</button>
{/if}