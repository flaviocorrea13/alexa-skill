export type BackendState =
    | "connected"
    | "addon_not_found"
    | "addon_stopped"
    | "ma_unavailable"
    | "config_incomplete"
    | "error";

export interface EntrySummary {
    entry_id: string;
    title: string;
    managed: boolean;
    addon_slug: string | null;
}

export interface EntriesResponse {
    entries: EntrySummary[];
    default_entry_id: string | null;
}

export interface Overview {
    entry: {
        entry_id: string;
        title: string;
        managed: boolean;
    };
    generated_at: string;
    state: BackendState;
    reason: string;
    stale: boolean;
    integration: {
        version: string | null;
        loaded: boolean;
        reachable: boolean;
        last_check: string | null;
        last_update_success: boolean;
        error: string | null;
    };
    addon: {
        available: boolean;
        installed: boolean | null;
        running: boolean | null;
        state: string | null;
        version: string | null;
        hostname: string | null;
        error: string | null;
    };
    music_assistant: {
        configured: boolean;
        level: string;
        stream_present: boolean;
        stream_https_ok: boolean;
    };
    alexa: {
        configured: boolean;
        configured_skill_id_masked: string | null;
        detected_skill_id_masked: string | null;
        skill_id_suggested: boolean | null;
        skill_id_matches: boolean | null;
        skill_linked: boolean | null;
        skill_found: boolean | null;
        endpoint_matches: boolean | null;
        testing_enabled: boolean | null;
    };
    checklist: {
        done: number;
        pending: number;
        blocked: number;
        attention: number;
        applicable: number;
        total: number;
        percent: number;
        complete: boolean;
        next_step: string | null;
        next_step_title: string | null;
    } | null;
    warnings: string[];
}

export interface RefreshResponse {
    success: boolean;
    /**
     * True only when the backend ran a coordinator update that finished
     * successfully. False means the cooldown or a concurrent refresh prevented
     * an update, and `overview` is the current snapshot.
     */
    refreshed: boolean;
    overview: Overview;
}
