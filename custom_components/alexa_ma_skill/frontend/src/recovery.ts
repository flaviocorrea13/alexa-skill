import type { EntriesResponse, EntrySummary, Overview } from "./types.js";

export interface RecoveryApi {
    entries(): Promise<EntriesResponse>;
    overview(entryId: string): Promise<Overview>;
}

export type RecoveryError = "recovery_failed";

export interface RecoveryResult {
    /**
     * True when the user changed the selection while the recovery was in
     * flight. The panel must discard everything else in the result, because
     * the newer selection owns the entry list and the overview.
     */
    stale: boolean;
    entries: EntrySummary[];
    selected: string | null;
    overview: Overview | null;
    error: RecoveryError | null;
}

/**
 * Return true when a WebSocket error is the stable ``entry_not_found`` code.
 *
 * Home Assistant rejects ``sendMessagePromise`` with an ``Error`` carrying the
 * backend error code, so no exception text needs to be parsed.
 */
export function isEntryNotFound(error: unknown): boolean {
    if (typeof error !== "object" || error === null) {
        return false;
    }
    return (error as { code?: unknown }).code === "entry_not_found";
}

/**
 * Decide whether a failed overview or refresh call should reload the entries.
 *
 * The recovery itself is guarded, so a second ``entry_not_found`` during the
 * recovery is surfaced as an error instead of starting another reload.
 */
export function shouldRecover(error: unknown, recovering: boolean): boolean {
    return !recovering && isEntryNotFound(error);
}

function staleResult(): RecoveryResult {
    return {
        stale: true,
        entries: [],
        selected: null,
        overview: null,
        error: null,
    };
}

function nextSelection(response: EntriesResponse): string | null {
    return response.default_entry_id ?? response.entries[0]?.entry_id ?? null;
}

/**
 * Reconcile the panel after the backend reported the selected entry missing.
 *
 * The list is reloaded exactly once. A removed selection is replaced by the
 * default entry or the first remaining entry; when nothing remains the result
 * has no selection so the panel can show its empty state. A backend that still
 * lists the entry it just reported missing is treated as an error instead of
 * triggering another reload, which keeps the recovery loop-free.
 *
 * ``isCurrent`` is consulted after every await. It must report whether the
 * selection that started the recovery is still the panel's selection; when it
 * is not, the result is marked stale so the caller leaves the newer selection
 * and its states untouched.
 */
export async function recoverRemovedEntry(
    api: RecoveryApi,
    previousSelected: string | null,
    isCurrent: () => boolean = () => true,
): Promise<RecoveryResult> {
    let response: EntriesResponse;
    try {
        response = await api.entries();
    } catch {
        if (!isCurrent()) {
            return staleResult();
        }
        return {
            stale: false,
            entries: [],
            selected: null,
            overview: null,
            error: "recovery_failed",
        };
    }

    if (!isCurrent()) {
        return staleResult();
    }

    const stillListed =
        previousSelected !== null &&
        response.entries.some((entry) => entry.entry_id === previousSelected);
    if (stillListed) {
        return {
            stale: false,
            entries: response.entries,
            selected: previousSelected,
            overview: null,
            error: "recovery_failed",
        };
    }

    const selected = nextSelection(response);
    if (selected === null) {
        return {
            stale: false,
            entries: response.entries,
            selected: null,
            overview: null,
            error: null,
        };
    }

    try {
        const overview = await api.overview(selected);
        if (!isCurrent()) {
            return staleResult();
        }
        return {
            stale: false,
            entries: response.entries,
            selected,
            overview,
            error: null,
        };
    } catch {
        if (!isCurrent()) {
            return staleResult();
        }
        return {
            stale: false,
            entries: response.entries,
            selected,
            overview: null,
            error: "recovery_failed",
        };
    }
}
