<script>
    export let userName = "John Doe"; // User's full name
    export let onLogout = () => {}; // Logout function

    // Compute user initials
    const initials = userName
        .split(" ")
        .map((n) => n[0])
        .join("")
        .toUpperCase();
</script>

<header
    class="flex items-center justify-between px-6 py-4 bg-white border-b border-gray-200 top-0 mb-1"
>
    <!-- Branding -->
    <a href="/" class="flex items-center space-x-3 hover:opacity-90">
        <img src="/logo.svg" alt="Logo" class="w-8 h-8" />
        <span class="text-2xl text-gray-800">
            Eigen<span class="font-bold">Task</span>
        </span>
    </a>

    <!-- Right controls -->
    <div class="flex items-center space-x-4">
        <!-- User Initials -->
        <div
            class="w-10 h-10 rounded-full bg-blue-500 text-white flex items-center justify-center font-semibold"
        >
            {initials}
        </div>

        <!-- Logout -->
        <button
            class="px-3 py-1 border border-gray-300 rounded-md hover:bg-gray-100"
            on:click={onLogout}
        >
            Logout
        </button>
    </div>
</header>
