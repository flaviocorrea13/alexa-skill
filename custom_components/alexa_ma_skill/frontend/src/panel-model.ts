import type { BackendState, Overview } from "./types.js";

export type UiState =
    | "loading"
    | "connected"
    | "stale"
    | "integration_not_loaded"
    | "addon_not_found"
    | "addon_stopped"
    | "ma_unavailable"
    | "config_incomplete"
    | "error";

export interface PanelView {
    state: UiState;
    stale: boolean;
    backendState: BackendState | null;
}

const KNOWN_STATES: ReadonlySet<BackendState> = new Set([
    "connected",
    "addon_not_found",
    "addon_stopped",
    "ma_unavailable",
    "config_incomplete",
    "error",
]);

export function initialView(): PanelView {
    return { state: "loading", stale: false, backendState: null };
}

export function viewFromOverview(
    overview: Overview | null,
    error: string | null,
): PanelView {
    if (error) {
        return { state: "error", stale: false, backendState: null };
    }
    if (overview === null) {
        return {
            state: "integration_not_loaded",
            stale: false,
            backendState: null,
        };
    }
    const backendState = KNOWN_STATES.has(overview.state)
        ? overview.state
        : "error";
    if (backendState === "connected" && overview.stale) {
        return { state: "stale", stale: true, backendState };
    }
    return {
        state: backendState,
        stale: overview.stale,
        backendState,
    };
}

export function isBusy(view: PanelView): boolean {
    return view.state === "loading";
}
