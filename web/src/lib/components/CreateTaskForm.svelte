<script lang="ts">
  import { env as publicEnv } from "$env/dynamic/public";
  import { createApiClient, type Task } from "$lib/apiClient";
  import Button from "$lib/components/ui/Button.svelte";
  import Input from "$lib/components/ui/Input.svelte";
  import Label from "$lib/components/ui/Label.svelte";
  import Textarea from "$lib/components/ui/Textarea.svelte";
  import { createEventDispatcher } from "svelte";

  const api = createApiClient({
    internalBaseUrl: publicEnv.PUBLIC_API_ORIGIN ?? "",
    externalBaseUrl: publicEnv.PUBLIC_API_ORIGIN ?? "",
  });

  const dispatch = createEventDispatcher<{
    close: void;
    created: { task: Task };
  }>();

  let title = "";
  let description = "";
  let plannedDuration: number | string | null = 60;
  let dueDate: string | null = null;
  let error: string | null = null;
  let loading = false;

  function close() {
    dispatch("close");
  }

  function normalizeDuration(value: number | string | null): number | undefined {
    if (value === null || value === "") return undefined;
    const n = typeof value === "string" ? Number(value) : value;
    if (Number.isNaN(n)) return undefined;
    return n;
  }

  async function submit() {
    const trimmedTitle = title.trim();
    const durationValue = normalizeDuration(plannedDuration);

    if (!trimmedTitle) {
      error = "Title is required.";
      return;
    }
    if (durationValue !== undefined && durationValue < 15) {
      error = "Estimated minutes must be at least 15.";
      return;
    }
    const normalizedDueDate = dueDate && dueDate.trim() ? dueDate : null;
    if (!normalizedDueDate) {
      error = "Due date is required.";
      return;
    }

    loading = true;
    error = null;

    const due_at = new Date(normalizedDueDate).toISOString();

    const res = await api.createTask({
      title: trimmedTitle,
      description: description.trim() || null,
      planned_duration: durationValue ?? undefined,
      due_at: due_at ?? undefined,
    });

    loading = false;

    if (!res.ok || !res.task) {
      error = res.error ?? "Unable to create task.";
      return;
    }

    dispatch("created", { task: res.task });
    dispatch("close");
  }
</script>

<form class="flex flex-col gap-4" on:submit|preventDefault={submit}>
  <div class="flex flex-col gap-1.5">
    <Label forId="create-title">Title</Label>
    <Input
      id="create-title"
      type="text"
      name="title"
      bind:value={title}
      placeholder="e.g. Draft project brief"
      required
    />
  </div>

  <div class="flex flex-col gap-1.5">
    <Label forId="create-description">Description (optional)</Label>
    <Textarea
      id="create-description"
      name="description"
      bind:value={description}
      placeholder="What needs to be done?"
      rows={3}
    />
  </div>

  <div class="flex flex-col gap-1.5">
    <Label forId="create-duration">Estimated minutes</Label>
    <Input
      id="create-duration"
      type="number"
      name="planned_duration"
      bind:value={plannedDuration}
      min={15}
      step={15}
    />
  </div>

  <div class="flex flex-col gap-1.5">
    <Label forId="create-due">Due date</Label>
    <Input
      id="create-due"
      type="date"
      name="due_at"
      bind:value={dueDate}
      required
    />
  </div>

  {#if error}
    <div
      class="text-sm text-rose-600 bg-rose-50 border border-rose-100 rounded-lg px-3 py-2"
      role="alert"
      id="create-error"
    >
      {error}
    </div>
  {/if}

  <div class="flex items-center gap-2 pt-1">
    <Button type="submit" variant="primary" disabled={loading}>
      {loading ? "Creating…" : "Create"}
    </Button>
    <Button type="button" variant="secondary" disabled={loading} on:click={close}>
      Cancel
    </Button>
  </div>
</form>
