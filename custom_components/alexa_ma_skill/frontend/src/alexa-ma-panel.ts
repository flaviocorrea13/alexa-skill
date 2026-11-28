import { LitElement, css, html, nothing } from "lit";
import { AlexaMaApi, type HassLike } from "./api.js";
import { languageFor, t } from "./localize.js";
import { initialView, viewFromOverview, type UiState } from "./panel-model.js";
import { shouldRecover, recoverRemovedEntry, type RecoveryResult } from "./recovery.js";
import type { EntriesResponse, EntrySummary, Overview } from "./types.js";

const ELEMENT_NAME = "alexa-ma-panel";

export class AlexaMaPanel extends LitElement {
    static properties = {
        hass: { attribute: false },
        narrow: { attribute: false },
        _loading: { state: true },
        _refreshing: { state: true },
        _entries: { state: true },
        _selected: { state: true },
        _overview: { state: true },
        _error: { state: true },
        _updatedAt: { state: true },
    };

    hass?: HassLike;
    narrow = false;

    private _api: AlexaMaApi | null = null;
    private _loading = true;
    private _refreshing = false;
    private _entries: EntrySummary[] = [];
    private _selected: string | null = null;
    private _overview: Overview | null = null;
    private _error: string | null = null;
    private _updatedAt: string | null = null;
    private _recovering = false;
    private _recoveryFailed = false;

    connectedCallback(): void {
        super.connectedCallback();
        void this._load();
    }

    protected updated(changed: Map<string, unknown>): void {
        if (changed.has("hass") && this.hass && !this._api) {
            void this._load();
        }
    }

    private async _load(): Promise<void> {
        if (!this.hass) {
            return;
        }
        this._loading = true;
        this._error = null;
        this._recoveryFailed = false;
        this._api = new AlexaMaApi(this.hass);
        try {
            const response = await this._api.entries();
            this._entries = response.entries;
            this._selectInitial(response);
            if (this._selected) {
                await this._loadOverview();
            } else {
                this._overview = null;
            }
        } catch (error) {
            if (shouldRecover(error, this._recovering)) {
                await this._runRecovery(this._selected);
            } else {
                this._error = this._label("load_failed");
                this._overview = null;
            }
        } finally {
            this._loading = false;
        }
    }

    private _selectInitial(response: EntriesResponse): void {
        if (
            this._selected &&
            this._entries.some((entry) => entry.entry_id === this._selected)
        ) {
            return;
        }
        this._selected =
            response.default_entry_id ?? this._entries[0]?.entry_id ?? null;
        this._overview = null;
        this._updatedAt = null;
    }

    private async _loadOverview(): Promise<void> {
        const entryId = this._selected;
        if (!this._api || !entryId) {
            return;
        }
        try {
            const overview = await this._api.overview(entryId);
            if (this._selected !== entryId) {
                return;
            }
            this._overview = overview;
            this._updatedAt = this._formatTime(overview.generated_at);
            this._error = null;
            this._recoveryFailed = false;
        } catch (error) {
            if (this._selected !== entryId) {
                return;
            }
            if (shouldRecover(error, this._recovering)) {
                await this._runRecovery(entryId);
                return;
            }
            throw error;
        }
    }

    private _applyRecoveryResult(result: RecoveryResult): void {
        this._entries = result.entries;
        this._selected = result.selected;
        this._overview = result.overview;
        this._updatedAt = result.overview
            ? this._formatTime(result.overview.generated_at)
            : null;
        this._error = result.error ? this._label(result.error) : null;
        this._recoveryFailed = result.error !== null;
    }

    private async _runRecovery(previousSelected: string | null): Promise<void> {
        if (!this._api || this._recovering) {
            return;
        }
        this._recovering = true;
        try {
            const result = await recoverRemovedEntry(
                this._api,
                previousSelected,
                () => this._selected === previousSelected,
            );
            if (result.stale) {
                // The user selected another entry while the recovery was in
                // flight; the newer selection owns the list and the overview.
                return;
            }
            this._applyRecoveryResult(result);
        } finally {
            this._recovering = false;
        }
    }

    private async _refresh(): Promise<void> {
        const entryId = this._selected;
        if (!this._api || !entryId || this._refreshing) {
            return;
        }
        this._refreshing = true;
        this._error = null;
        this._recoveryFailed = false;
        try {
            const response = await this._api.refresh(entryId);
            if (this._selected !== entryId) {
                return;
            }
            this._overview = response.overview;
            this._updatedAt = this._formatTime(response.overview.generated_at);
        } catch (error) {
            if (this._selected !== entryId) {
                return;
            }
            if (shouldRecover(error, this._recovering)) {
                await this._runRecovery(entryId);
            } else {
                this._error = this._label("refresh_failed");
            }
        } finally {
            this._refreshing = false;
        }
    }

    private async _changeEntry(event: Event): Promise<void> {
        const select = event.target as HTMLSelectElement;
        this._selected = select.value || null;
        this._overview = null;
        this._loading = true;
        this._recoveryFailed = false;
        try {
            await this._loadOverview();
        } catch (error) {
            if (shouldRecover(error, this._recovering)) {
                await this._runRecovery(this._selected);
            } else {
                this._error = this._label("load_failed");
            }
        } finally {
            this._loading = false;
        }
    }

    private _label(key: string): string {
        return t(languageFor(this.hass?.language), key);
    }

    private _formatTime(value: string | null): string {
        if (!value) {
            return this._label("never");
        }
        const date = new Date(value);
        if (Number.isNaN(date.getTime())) {
            return this._label("unknown");
        }
        return date.toLocaleString();
    }

    private _stateLabel(state: UiState): string {
        return this._label(state);
    }

    private _value(value: unknown): string {
        if (value === null || value === undefined || value === "") {
            return this._label("unknown");
        }
        if (typeof value === "boolean") {
            return this._label(value ? "yes" : "no");
        }
        return String(value);
    }

    private _renderOverview(overview: Overview) {
        const view = viewFromOverview(overview, this._error);
        const checklist = overview.checklist;
        return html`
            <div class="status-line">
                <span class="badge ${view.state}">${this._stateLabel(view.state)}</span>
                ${view.stale
                    ? html`<span class="stale">${this._label("stale")}</span>`
                    : nothing}
            </div>
            ${this._error
                ? html`<div class="error" role="alert">${this._error}</div>`
                : nothing}
            <div class="grid">
                <section class="card">
                    <h2>${this._label("integration")}</h2>
                    <dl>
                        <dt>${this._label("version")}</dt>
                        <dd>${this._value(overview.integration.version)}</dd>
                        <dt>${this._label("reachable")}</dt>
                        <dd>${this._value(overview.integration.reachable)}</dd>
                    </dl>
                </section>
                <section class="card">
                    <h2>${this._label("addon")}</h2>
                    <dl>
                        <dt>${this._label("installed")}</dt>
                        <dd>${this._value(overview.addon.installed)}</dd>
                        <dt>${this._label("running")}</dt>
                        <dd>${this._value(overview.addon.running)}</dd>
                        <dt>${this._label("version")}</dt>
                        <dd>${this._value(overview.addon.version)}</dd>
                        <dt>${this._label("state")}</dt>
                        <dd>${this._value(overview.addon.state)}</dd>
                    </dl>
                </section>
                <section class="card">
                    <h2>${this._label("music_assistant")}</h2>
                    <dl>
                        <dt>${this._label("configured")}</dt>
                        <dd>${this._value(overview.music_assistant.configured)}</dd>
                        <dt>${this._label("state")}</dt>
                        <dd>${this._value(overview.music_assistant.level)}</dd>
                        <dt>${this._label("stream")}</dt>
                        <dd>${this._value(overview.music_assistant.stream_present)}</dd>
                        <dt>${this._label("stream_ok")}</dt>
                        <dd>${this._value(overview.music_assistant.stream_https_ok)}</dd>
                    </dl>
                </section>
                <section class="card">
                    <h2>${this._label("alexa")}</h2>
                    <dl>
                        <dt>${this._label("configured")}</dt>
                        <dd>${this._value(overview.alexa.configured)}</dd>
                        <dt>${this._label("state")}</dt>
                        <dd>${this._value(overview.alexa.skill_linked)}</dd>
                        <dt>${this._label("skill_id")}</dt>
                        <dd class="mono">
                            ${this._value(overview.alexa.configured_skill_id_masked)}
                        </dd>
                        <dt>${this._label("detected_skill_id")}</dt>
                        <dd class="mono">
                            ${this._value(overview.alexa.detected_skill_id_masked)}
                        </dd>
                        <dt>${this._label("skill_id_matches")}</dt>
                        <dd>${this._value(overview.alexa.skill_id_matches)}</dd>
                    </dl>
                    ${overview.alexa.skill_id_suggested
                        ? html`<p class="hint">
                              ${this._label("skill_id_suggested")}
                          </p>`
                        : nothing}
                </section>
                <section class="card wide">
                    <h2>${this._label("checklist")}</h2>
                    ${checklist
                        ? html`
                              <p class="progress">
                                  ${this._label("progress")}:
                                  ${checklist.done}/${checklist.applicable}
                                  (${checklist.percent}%)
                              </p>
                              <p>
                                  ${this._label("next_step")}:
                                  ${this._value(checklist.next_step_title)}
                              </p>
                          `
                        : html`<p>${this._label("unknown")}</p>`}
                </section>
            </div>
            ${overview.warnings.length
                ? html`
                      <section class="card wide">
                          <h2>${this._label("warnings")}</h2>
                          <ul>
                              ${overview.warnings.map(
                                  (warning) => html`<li>${warning}</li>`,
                              )}
                          </ul>
                      </section>
                  `
                : nothing}
            <p class="updated">
                ${this._label("last_update")}: ${this._updatedAt ?? this._label("never")}
            </p>
        `;
    }

    private _renderEmptyState() {
        if (this._recoveryFailed) {
            return html`
                <div class="empty">
                    <p>${this._label("recovery_failed")}</p>
                    <button
                        class="refresh"
                        ?disabled=${this._recovering}
                        @click=${() =>
                            void this._runRecovery(this._selected)}
                    >
                        ${this._recovering
                            ? this._label("loading")
                            : this._label("retry")}
                    </button>
                </div>
            `;
        }
        return html`
            <div class="empty">
                <p>${this._label("no_entries")}</p>
                ${this._error
                    ? html`<p class="error">${this._error}</p>`
                    : nothing}
            </div>
        `;
    }

    render() {
        const view = this._loading && !this._overview
            ? initialView()
            : viewFromOverview(this._overview, this._error);
        return html`
            <div class="page">
                <header class="header">
                    <div>
                        <h1>${this._label("title")}</h1>
                        <p>${this._label("subtitle")}</p>
                    </div>
                    <button
                        class="refresh"
                        ?disabled=${this._refreshing || !this._selected}
                        @click=${() => void this._refresh()}
                    >
                        ${this._refreshing
                            ? this._label("refreshing")
                            : this._label("refresh")}
                    </button>
                </header>
                ${this._entries.length > 1
                    ? html`
                          <label class="entry-select">
                              ${this._label("select_entry")}
                              <select
                                  .value=${this._selected ?? ""}
                                  @change=${(event: Event) =>
                                      void this._changeEntry(event)}
                              >
                                  ${this._entries.map(
                                      (entry) => html`
                                          <option value=${entry.entry_id}>
                                              ${entry.title}
                                          </option>
                                      `,
                                  )}
                              </select>
                          </label>
                      `
                    : nothing}
                ${view.state === "loading"
                    ? html`<div class="loading" role="status">
                          <span class="spinner"></span>
                          ${this._label("loading")}
                      </div>`
                    : this._overview
                      ? this._renderOverview(this._overview)
                      : this._renderEmptyState()}
            </div>
        `;
    }

    static styles = css`
        :host {
            display: block;
            padding: 16px;
            color: var(--primary-text-color);
        }
        .page {
            max-width: 1100px;
            margin: 0 auto;
        }
        .header {
            display: flex;
            gap: 16px;
            align-items: flex-start;
            justify-content: space-between;
            flex-wrap: wrap;
            margin-bottom: 16px;
        }
        h1 {
            margin: 0;
            font-size: 1.8rem;
        }
        h2 {
            margin: 0 0 8px;
            font-size: 1rem;
        }
        .header p {
            margin: 4px 0 0;
            color: var(--secondary-text-color);
        }
        .refresh {
            border: 0;
            border-radius: 6px;
            padding: 10px 16px;
            cursor: pointer;
            color: var(--text-primary-color);
            background: var(--primary-color);
            font: inherit;
        }
        .refresh:disabled {
            opacity: 0.55;
            cursor: default;
        }
        .entry-select {
            display: flex;
            flex-direction: column;
            gap: 4px;
            margin-bottom: 16px;
            max-width: 420px;
        }
        select {
            padding: 8px;
            border-radius: 6px;
            border: 1px solid var(--divider-color);
            background: var(--card-background-color);
            color: var(--primary-text-color);
        }
        .status-line {
            display: flex;
            gap: 10px;
            align-items: center;
            margin-bottom: 16px;
            flex-wrap: wrap;
        }
        .badge,
        .stale {
            display: inline-block;
            border-radius: 999px;
            padding: 6px 12px;
            font-weight: 600;
        }
        .badge.connected {
            background: var(--success-color);
            color: #fff;
        }
        .badge.error,
        .badge.addon_not_found,
        .badge.addon_stopped,
        .badge.ma_unavailable {
            background: var(--error-color);
            color: #fff;
        }
        .badge.config_incomplete,
        .badge.stale {
            background: var(--warning-color);
            color: #000;
        }
        .stale {
            background: var(--warning-color);
            color: #000;
        }
        .grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(230px, 1fr));
            gap: 12px;
        }
        .card {
            border: 1px solid var(--divider-color);
            border-radius: 10px;
            padding: 14px;
            background: var(--card-background-color);
        }
        .card.wide {
            grid-column: 1 / -1;
        }
        dl {
            display: grid;
            grid-template-columns: 1fr auto;
            gap: 6px 14px;
            margin: 0;
        }
        dt {
            color: var(--secondary-text-color);
        }
        dd {
            margin: 0;
            text-align: right;
            overflow-wrap: anywhere;
        }
        .mono {
            font-family: var(--code-font-family, monospace);
            font-size: 0.9rem;
        }
        .hint {
            margin: 10px 0 0;
            color: var(--secondary-text-color);
            font-size: 0.9rem;
        }
        .loading,
        .empty {
            display: flex;
            gap: 10px;
            align-items: center;
            padding: 24px;
            border: 1px dashed var(--divider-color);
            border-radius: 10px;
        }
        .spinner {
            width: 18px;
            height: 18px;
            border: 2px solid var(--divider-color);
            border-top-color: var(--primary-color);
            border-radius: 50%;
            animation: spin 0.8s linear infinite;
        }
        .error {
            margin: 12px 0;
            padding: 10px 12px;
            border-radius: 8px;
            background: var(--error-color);
            color: #fff;
        }
        .updated {
            margin-top: 16px;
            color: var(--secondary-text-color);
            font-size: 0.9rem;
        }
        @keyframes spin {
            to {
                transform: rotate(360deg);
            }
        }
        @media (max-width: 600px) {
            :host {
                padding: 10px;
            }
            .header {
                align-items: stretch;
            }
            .refresh {
                width: 100%;
            }
        }
    `;
}

if (!customElements.get(ELEMENT_NAME)) {
    customElements.define(ELEMENT_NAME, AlexaMaPanel);
}
