import type { PageLoad } from './$types';

export const load: PageLoad = async () => {
    const API_URL = "http://localhost:8000";

    let data = {
        // Returns {"authenticated" : true, "user" : ...} or {"authenticated" : false}
        isAuthenticated: await fetch(`${API_URL}/auth/status`, { credentials: "include" }).then(res => res.json()).then(res => res.authenticated)
    }

    return data;
}