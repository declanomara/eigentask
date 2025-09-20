<script lang="ts">
    import Header from "./Header.svelte";

    const API_URL = "http://localhost:8000";

    const handleLogin = () => {
        // Handle OIDC login flow using backend
        // 1. Redirect to {API_URL}/auth/login
        // 2. Backend redirects to Keycloak
        // 3. Keycloak redirects back to {API_URL}/callback
        // 4. Backend processes callback and sets cookies
        // 5. Redirect back to original page

        const returnTo = window.location.href;
        window.location.href = `${API_URL}/auth/login?return_to=${encodeURIComponent(returnTo)}`;
    }

    const handleLogout = () => {
        // Handle OIDC logout flow using backend
        // 1. Redirect to {API_URL}/auth/logout
        // 2. Backend redirects to Keycloak
        // 3. Keycloak redirects back to {API_URL}/callback
        // 4. Backend processes callback and clears cookies
        // 5. Redirect back to original page

        const returnTo = window.location.href;
        window.location.href = `${API_URL}/auth/logout?return_to=${encodeURIComponent(returnTo)}`;
    }

    let { data } = $props();
    let isAuthenticated = data?.isAuthenticated;
</script>

<Header isAuthenticated={isAuthenticated} onLogin={handleLogin} onLogout={handleLogout} />