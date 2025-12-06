// Minimal, local implementation of the `svelte-dnd-action` API used by the app.
// It supports basic drag and drop between named zones and emits `consider` and
// `finalize` events with pointer coordinates so consumers can compute drop
// positions. This is intentionally lightweight to work in offline environments.
// Minimal type re-definition to avoid importing from svelte/action in the browser bundle.
const DEBUG = true;

export type Action<ElementType = HTMLElement, Parameter = any> = (
    node: ElementType,
    parameters: Parameter,
) => {
    update?: (parameters: Parameter) => void;
    destroy?: () => void;
};

export type DndItem = { id: string | number } & Record<string, unknown>;

export type DndZoneOptions<T extends DndItem> = {
    /** Unique identifier for the dropzone so sources/destinations can be distinguished. */
    id?: string;
    /** Items present in this zone (used to look up metadata for the dragged element). */
    items: T[];
    /** Optional custom id resolver. */
    getItemId?: (item: T) => string | number;
};

export type DndEventInfo<T extends DndItem> = {
    trigger: "dragover" | "drop";
    source: { id: string; item: T | null } | null;
    destination: { id: string; node: HTMLElement } | null;
    pointer: { clientX: number; clientY: number };
};

export type DndEvent<T extends DndItem> = {
    items: T[];
    info: DndEventInfo<T>;
};

let dragCounter = 0;
let activeDrag:
    | {
          zoneId: string;
          item: DndItem | null;
      }
    | null = null;

const defaultGetId = (item: DndItem) => item.id;
const toKey = (value: string | number) => String(value);

export const dndzone: Action<HTMLElement, DndZoneOptions<DndItem>> = (
    node: HTMLElement,
    options: DndZoneOptions<DndItem>,
) => {
    let opts = options;
    let zoneId = opts.id ?? `dnd-zone-${++dragCounter}`;
    let getId = opts.getItemId ?? defaultGetId;

    const resolveItem = (id: string | number): DndItem | null => {
        const needle = toKey(id);
        return opts.items.find((item) => toKey(getId(item)) === needle) ?? null;
    };

    function dispatchEvent(
        name: "consider" | "finalize",
        trigger: "dragover" | "drop",
        event: DragEvent,
        itemOverride?: DndItem | null,
    ) {
        const detail: DndEvent<DndItem> = {
            items: opts.items,
            info: {
                trigger,
                source: activeDrag ? { id: activeDrag.zoneId, item: activeDrag.item } : null,
                destination: { id: zoneId, node },
                pointer: { clientX: event.clientX, clientY: event.clientY },
            },
        };
        if (itemOverride !== undefined) {
            detail.info.source = { id: activeDrag?.zoneId ?? zoneId, item: itemOverride };
        }
        if (DEBUG) {
            // eslint-disable-next-line no-console
            console.log("[dndzone]", name, { zoneId, trigger, source: detail.info.source, dest: detail.info.destination?.id, pointer: detail.info.pointer });
        }
        node.dispatchEvent(new CustomEvent(name, { detail, bubbles: true }));
    }

    function handleDragStart(event: DragEvent) {
        const target = (event.target as HTMLElement | null)?.closest<HTMLElement>("[data-dnd-id]");
        if (!target) return;
        const id = target.dataset.dndId;
        if (!id) return;
        const item = resolveItem(id) ?? ({ id } as DndItem);
        activeDrag = { zoneId, item };
        event.dataTransfer?.setData("application/json", JSON.stringify({ id }));
        // Center the drag image on the cursor for a more natural feel.
        const imgX = (target.clientWidth ?? 0) / 2;
        const imgY = (target.clientHeight ?? 0) / 2;
        event.dataTransfer?.setDragImage(target, imgX, imgY);
        if (DEBUG) {
            // eslint-disable-next-line no-console
            console.log("[dndzone] dragstart", { zoneId, id, hasItem: Boolean(item) });
        }
    }

    function handleDragOver(event: DragEvent) {
        if (!activeDrag) return;
        event.preventDefault();
        dispatchEvent("consider", "dragover", event);
    }

    function handleDrop(event: DragEvent) {
        if (!activeDrag) return;
        event.preventDefault();
        dispatchEvent("finalize", "drop", event, activeDrag.item);
        activeDrag = null;
    }

    function handleDragEnd() {
        if (DEBUG && activeDrag) {
            // eslint-disable-next-line no-console
            console.log("[dndzone] dragend", { zoneId: activeDrag.zoneId });
        }
        activeDrag = null;
    }

    // Use capture for dragstart so we reliably catch events from child draggables.
    node.addEventListener("dragstart", handleDragStart, true);
    node.addEventListener("dragover", handleDragOver);
    node.addEventListener("drop", handleDrop);
    node.addEventListener("dragend", handleDragEnd);

    return {
        update(newOptions: DndZoneOptions<DndItem>) {
            opts = newOptions;
            zoneId = opts.id ?? zoneId;
            getId = opts.getItemId ?? defaultGetId;
        },
        destroy() {
            node.removeEventListener("dragstart", handleDragStart, true);
            node.removeEventListener("dragover", handleDragOver);
            node.removeEventListener("drop", handleDrop);
            node.removeEventListener("dragend", handleDragEnd);
        },
    };
};


