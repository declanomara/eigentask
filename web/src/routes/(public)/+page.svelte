<svelte:head>
    <title>Eigentask · Plan, schedule, and finish your day</title>
    <meta
        name="description"
        content="Eigentask helps you capture, schedule, and complete your day’s work with a fast, focused workflow."
    />
</svelte:head>

<div class="min-h-screen bg-gradient-to-br from-slate-50 via-white to-slate-100 text-gray-800">
    <div class="max-w-6xl mx-auto px-4 sm:px-6 lg:px-8 py-6 flex flex-col gap-8">
        <header class="flex items-center justify-between">
            <div class="flex items-center gap-3">
                <div class="h-10 w-10 rounded-2xl bg-blue-600 text-white flex items-center justify-center font-semibold shadow-md">
                    ET
                </div>
                <div>
                    <p class="text-sm uppercase tracking-wide text-gray-500">Eigentask</p>
                    <h1 class="text-xl font-semibold text-gray-900">Plan. Schedule. Finish.</h1>
                </div>
            </div>
            <a
                href="/app"
                class="hidden sm:inline-flex items-center gap-2 px-4 py-2 rounded-xl bg-blue-600 text-white text-sm font-medium shadow-sm hover:bg-blue-700 transition"
            >
                Open App →
            </a>
        </header>

        <main class="grid grid-cols-1 lg:grid-cols-2 gap-8 items-center">
            <div class="space-y-5">
                <div class="space-y-2">
                    <p class="text-sm uppercase tracking-wide text-blue-600 font-semibold">Stay in flow</p>
                    <h2 class="text-3xl sm:text-4xl font-bold text-gray-900 leading-tight">
                        Turn today’s intent into a schedule you can finish.
                    </h2>
                    <p class="text-lg text-gray-600 leading-relaxed">
                        Eigentask keeps backlog, schedule, and completion in one place.
                        Drag tasks onto your timeline, mark them done, and keep moving.
                    </p>
                </div>
                <div class="flex flex-col sm:flex-row gap-3">
                    <a
                        href="/app"
                        class="inline-flex items-center justify-center px-5 py-3 rounded-xl bg-blue-600 text-white text-sm font-semibold shadow-md hover:bg-blue-700 transition"
                    >
                        Go to app
                    </a>
                    <a
                        href="/app#learn"
                        class="inline-flex items-center justify-center px-5 py-3 rounded-xl border border-gray-200 text-sm font-semibold text-gray-800 bg-white hover:border-gray-300 shadow-sm transition"
                    >
                        See how it works
                    </a>
                </div>
                <div class="grid grid-cols-1 sm:grid-cols-2 gap-2">
                    <div class="rounded-2xl border border-gray-200 bg-white p-4 shadow-sm space-y-2">
                        <p class="text-sm uppercase tracking-wide text-blue-600 font-semibold">Philosophy</p>
                        <p class="text-sm text-gray-700 leading-relaxed">
                            Opinionated on purpose: fast capture, simple scheduling, nothing forgotten.
                            Spend energy on doing, not managing.
                        </p>
                        <div class="flex flex-wrap gap-2 text-xs text-gray-600">
                            <span class="px-3 py-1 rounded-full bg-blue-50 text-blue-700 border border-blue-100">Never forget</span>
                            <span class="px-3 py-1 rounded-full bg-gray-50 text-gray-700 border border-gray-200">Simple on purpose</span>
                            <span class="px-3 py-1 rounded-full bg-emerald-50 text-emerald-700 border border-emerald-100">Finish more</span>
                        </div>
                    </div>
                    <div class="rounded-2xl border border-gray-200 bg-white p-4 shadow-sm space-y-2">
                        <div class="flex items-center gap-2">
                            <p class="text-sm uppercase tracking-wide text-blue-600 font-semibold">Coming soon</p>
                            <span class="text-[11px] px-2 py-1 rounded-full bg-amber-50 text-amber-800 border border-amber-200">Roadmap</span>
                        </div>
                        <div class="space-y-2 text-sm text-gray-700">
                            <div>
                                <p class="font-semibold text-gray-900">Quick task creation (AI)</p>
                                <p class="text-gray-600">Capture tasks in seconds with smart suggestions.</p>
                            </div>
                            <div>
                                <p class="font-semibold text-gray-900">Auto scheduling (ML)</p>
                                <p class="text-gray-600">Let the system place tasks into your day intelligently.</p>
                            </div>
                        </div>
                    </div>
                </div>
            </div>

            <div class="relative">
                <div class="absolute inset-0 blur-3xl bg-blue-100 opacity-60 rounded-[28px]"></div>
                <div class="relative rounded-3xl border border-gray-200 bg-white shadow-xl p-4 sm:p-5 space-y-3">
                    <div class="flex items-center justify-between">
                        <div>
                            <p class="text-xs uppercase text-gray-500 tracking-wide">Today</p>
                            <p class="text-lg font-semibold text-gray-900">Your schedule</p>
                        </div>
                        <span class="text-xs px-3 py-1 rounded-full bg-blue-50 text-blue-700 border border-blue-200">
                            Focus mode
                        </span>
                    </div>
                    <div class="border border-dashed border-gray-200 rounded-2xl bg-gray-50 p-4 space-y-3">
                        <div class="flex items-center gap-3">
                            <span class="h-3 w-3 rounded-full bg-blue-500"></span>
                            <div>
                                <p class="text-sm font-semibold text-gray-900">Draft proposal</p>
                                <p class="text-xs text-gray-500">09:30–10:30</p>
                            </div>
                        </div>
                        <div class="flex items-center gap-3">
                            <span class="h-3 w-3 rounded-full bg-blue-500"></span>
                            <div>
                                <p class="text-sm font-semibold text-gray-900">Review timeline</p>
                                <p class="text-xs text-gray-500">11:00–12:00</p>
                            </div>
                        </div>
                        <div class="flex items-center gap-3 opacity-80">
                            <span class="h-3 w-3 rounded-full bg-gray-400"></span>
                            <div>
                                <p class="text-sm font-semibold text-gray-800">Ship updates</p>
                                <p class="text-xs text-gray-500">Completed</p>
                            </div>
                        </div>
                    </div>
                    <div class="flex items-center justify-between">
                        <div class="flex items-center gap-2 text-sm text-gray-600">
                            <span class="h-2 w-2 rounded-full bg-blue-500"></span> Scheduled
                            <span class="h-2 w-2 rounded-full bg-gray-400 ml-3"></span> Completed
                        </div>
                        <a href="/app" class="text-sm font-semibold text-blue-600 hover:text-blue-700">Open app →</a>
                    </div>
                </div>
            </div>
        </main>

        <footer class="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-2 text-sm text-gray-500">
            <span>Designed for focus. Built for finishing.</span>
            <a href="/app" class="text-blue-600 font-semibold hover:text-blue-700">Start now →</a>
        </footer>
    </div>
</div>
