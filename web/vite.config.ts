import { sveltekit } from "@sveltejs/kit/vite";
import { resolve } from "path";
import { defineConfig } from "vite";

export default defineConfig({
    plugins: [sveltekit()],
    resolve: {
        alias: {
            "svelte-dnd-action": resolve("./src/lib/vendor/svelte-dnd-action"),
        },
    },
});
