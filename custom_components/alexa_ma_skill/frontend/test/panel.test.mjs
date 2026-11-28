import assert from "node:assert/strict";
import test from "node:test";

// Minimal browser globals so the Lit element can be imported in Node. Element
// instances are created with Object.create(), so no DOM machinery runs.
if (!globalThis.window) {
    globalThis.window = globalThis;
}
if (!globalThis.HTMLElement) {
    globalThis.HTMLElement = class HTMLElement {};
}
if (!globalThis.customElements) {
    globalThis.customElements = {
        define() {},
        get() {
            return undefined;
        },
    };
}

const { AlexaMaPanel } = await import("../.test-build/alexa-ma-panel.js");

function entry(entryId) {
    return { entry_id: entryId, title: entryId, managed: true, addon_slug: null };
}

function overviewFor(entryId) {
    return {
        entry: { entry_id: entryId, title: entryId, managed: true },
        generated_at: "2026-11-25T00:00:00+00:00",
    };
}

function makePanel() {
    const panel = Object.create(AlexaMaPanel.prototype);
    panel.hass = { connection: {}, language: "pt-BR" };
    panel._loading = false;
    panel._refreshing = false;
    panel._entries = [];
    panel._selected = null;
    panel._overview = null;
    panel._error = null;
    panel._updatedAt = null;
    panel._recovering = false;
    panel._recoveryFailed = false;
    return panel;
}

function makePanelWithConnection(handler) {
    const panel = makePanel();
    panel.hass = {
        connection: {
            async sendMessagePromise(message) {
                return handler(message);
            },
        },
        language: "pt-BR",
    };
    return panel;
}

function fakeApi({ entries, entriesError = null, overviewError = null } = {}) {
    const api = {
        entryCalls: 0,
        overviewCalls: [],
        async entries() {
            api.entryCalls += 1;
            if (entriesError) {
                throw entriesError;
            }
            return entries ?? { entries: [], default_entry_id: null };
        },
        async overview(entryId) {
            api.overviewCalls.push(entryId);
            if (overviewError) {
                throw overviewError;
            }
            return overviewFor(entryId);
        },
    };
    return api;
}

test("a completed recovery applies the result when the selection is unchanged", async () => {
    const panel = makePanel();
    panel._selected = "a";
    panel._api = fakeApi({
        entries: { entries: [entry("b")], default_entry_id: "b" },
    });

    await panel._runRecovery("a");

    assert.equal(panel._selected, "b");
    assert.equal(panel._overview.entry.entry_id, "b");
    assert.equal(panel._recoveryFailed, false);
    assert.equal(panel._error, null);
    assert.equal(panel._recovering, false);
});

test("a selection changed during entries() is not overwritten", async () => {
    const panel = makePanel();
    panel._selected = "a";
    panel._overview = overviewFor("b");
    const api = {
        entryCalls: 0,
        overviewCalls: [],
        async entries() {
            api.entryCalls += 1;
            // The user picks B while the recovery waits for the list.
            panel._selected = "b";
            return { entries: [entry("b")], default_entry_id: null };
        },
        async overview(entryId) {
            api.overviewCalls.push(entryId);
            return overviewFor(entryId);
        },
    };
    panel._api = api;

    await panel._runRecovery("a");

    assert.equal(panel._selected, "b");
    assert.equal(panel._overview.entry.entry_id, "b");
    assert.deepEqual(api.overviewCalls, []);
    assert.equal(panel._recoveryFailed, false);
    assert.equal(panel._recovering, false);
});

test("a selection changed during the overview keeps the newer state", async () => {
    const panel = makePanel();
    panel._selected = "a";
    let resolveOverview;
    const api = {
        entryCalls: 0,
        overviewCalls: [],
        async entries() {
            api.entryCalls += 1;
            return { entries: [entry("b")], default_entry_id: "b" };
        },
        overview(entryId) {
            api.overviewCalls.push(entryId);
            return new Promise((resolve) => {
                resolveOverview = resolve;
            });
        },
    };
    panel._api = api;

    const pending = panel._runRecovery("a");
    await Promise.resolve();
    assert.deepEqual(api.overviewCalls, ["b"]);

    // The user selects B while the recovery's overview is in flight.
    panel._selected = "b";
    panel._overview = overviewFor("b");
    panel._error = "owned-by-b";
    resolveOverview(overviewFor("b"));
    await pending;

    assert.equal(panel._selected, "b");
    assert.equal(panel._overview.entry.entry_id, "b");
    assert.equal(panel._error, "owned-by-b");
    assert.equal(panel._recovering, false);
});

test("a failed recovery exposes the retry state", async () => {
    const panel = makePanel();
    panel._selected = "a";
    panel._api = fakeApi({ entriesError: new Error("offline") });

    await panel._runRecovery("a");

    assert.equal(panel._recoveryFailed, true);
    assert.equal(panel._entries.length, 0);
    assert.equal(panel._selected, null);
    assert.equal(panel._overview, null);
    assert.ok(panel._error && panel._error.length > 0);
});

test("a legitimate empty state does not expose the retry state", async () => {
    const panel = makePanel();
    panel._selected = "a";
    panel._api = fakeApi({
        entries: { entries: [], default_entry_id: null },
    });

    await panel._runRecovery("a");

    assert.equal(panel._recoveryFailed, false);
    assert.equal(panel._selected, null);
    assert.equal(panel._error, null);
});

test("a retry selects the single remaining entry", async () => {
    const panel = makePanel();
    panel._recoveryFailed = true;
    panel._api = fakeApi({
        entries: { entries: [entry("solo")], default_entry_id: "solo" },
    });

    await panel._runRecovery(panel._selected);

    assert.equal(panel._selected, "solo");
    assert.equal(panel._overview.entry.entry_id, "solo");
    assert.equal(panel._recoveryFailed, false);
    assert.equal(panel._error, null);
});

test("a retry respects the selection rule with several entries", async () => {
    const panel = makePanel();
    panel._recoveryFailed = true;
    panel._api = fakeApi({
        entries: {
            entries: [entry("a"), entry("c")],
            default_entry_id: null,
        },
    });

    await panel._runRecovery(panel._selected);

    assert.equal(panel._selected, "a");
    assert.equal(panel._overview.entry.entry_id, "a");
    assert.equal(panel._recoveryFailed, false);
});

test("a retry without entries ends in the legitimate empty state", async () => {
    const panel = makePanel();
    panel._recoveryFailed = true;
    panel._error = "stale message";
    panel._api = fakeApi({
        entries: { entries: [], default_entry_id: null },
    });

    await panel._runRecovery(panel._selected);

    assert.equal(panel._selected, null);
    assert.equal(panel._recoveryFailed, false);
    assert.equal(panel._error, null);
});

test("a retry that fails again keeps the retry state", async () => {
    const panel = makePanel();
    panel._recoveryFailed = true;
    panel._api = fakeApi({ entriesError: new Error("offline") });

    await panel._runRecovery(panel._selected);

    assert.equal(panel._recoveryFailed, true);
    assert.equal(panel._overview, null);
    assert.ok(panel._error && panel._error.length > 0);
});

test("a repeated retry does not start concurrent recoveries", async () => {
    const panel = makePanel();
    panel._selected = "a";
    let resolveEntries;
    const api = {
        entryCalls: 0,
        overviewCalls: [],
        entries() {
            api.entryCalls += 1;
            return new Promise((resolve) => {
                resolveEntries = resolve;
            });
        },
        async overview(entryId) {
            api.overviewCalls.push(entryId);
            return overviewFor(entryId);
        },
    };
    panel._api = api;

    const first = panel._runRecovery("a");
    const second = panel._runRecovery("a");
    await second;
    assert.equal(api.entryCalls, 1);

    resolveEntries({ entries: [entry("b")], default_entry_id: "b" });
    await first;
    assert.equal(panel._selected, "b");
    assert.equal(api.entryCalls, 1);
});

test("a load clears a previous recovery failure", async () => {
    const panel = makePanelWithConnection((message) => {
        if (message.type === "alexa_ma_skill/entries") {
            return { entries: [entry("b")], default_entry_id: "b" };
        }
        if (message.type === "alexa_ma_skill/overview") {
            return overviewFor("b");
        }
        throw new Error(`unexpected command ${message.type}`);
    });
    panel._recoveryFailed = true;
    panel._selected = "a";

    await panel._load();

    assert.equal(panel._recoveryFailed, false);
    assert.equal(panel._selected, "b");
    assert.equal(panel._loading, false);
});

test("a failed refresh is not a recovery failure", async () => {
    const panel = makePanel();
    panel._selected = "a";
    panel._entries = [entry("a")];
    panel._api = {
        async refresh() {
            throw { code: "refresh_failed" };
        },
    };

    await panel._refresh();

    assert.equal(panel._recoveryFailed, false);
    assert.equal(panel._overview, null);
    assert.ok(panel._error && panel._error.length > 0);
    assert.equal(panel._refreshing, false);
});

test("a removed entry during refresh falls back to the recovery", async () => {
    const panel = makePanel();
    panel._selected = "a";
    panel._recoveryFailed = false;
    panel._api = {
        async refresh() {
            throw { code: "entry_not_found" };
        },
        async entries() {
            throw new Error("offline");
        },
        async overview() {
            throw new Error("must not load an overview");
        },
    };

    await panel._refresh();

    assert.equal(panel._recoveryFailed, true);
    assert.equal(panel._refreshing, false);
    assert.equal(panel._overview, null);
});

test("a successful refresh clears the recovery state", async () => {
    const panel = makePanel();
    panel._selected = "a";
    panel._recoveryFailed = true;
    panel._api = {
        async refresh() {
            return {
                success: true,
                refreshed: true,
                overview: overviewFor("a"),
            };
        },
    };

    await panel._refresh();

    assert.equal(panel._overview.entry.entry_id, "a");
    assert.equal(panel._recoveryFailed, false);
    assert.equal(panel._error, null);
    assert.equal(panel._refreshing, false);
});

test("the retry action is rendered only in the recovery failure state", () => {
    const failed = makePanel();
    failed._recoveryFailed = true;
    failed._error = failed._label("recovery_failed");
    const failedHtml = failed._renderEmptyState().strings.join("");
    assert.ok(failedHtml.includes('class="refresh"'));
    assert.ok(failedHtml.includes("<button"));

    const empty = makePanel();
    empty._recoveryFailed = false;
    empty._error = null;
    const emptyHtml = empty._renderEmptyState().strings.join("");
    assert.ok(!emptyHtml.includes('class="refresh"'));
    assert.ok(!emptyHtml.includes("<button"));
});
