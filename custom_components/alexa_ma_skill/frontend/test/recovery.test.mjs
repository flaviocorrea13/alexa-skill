import assert from "node:assert/strict";
import test from "node:test";

import {
    isEntryNotFound,
    recoverRemovedEntry,
    shouldRecover,
} from "../.test-build/recovery.js";

function entry(entryId, title = entryId) {
    return { entry_id: entryId, title, managed: true, addon_slug: null };
}

function overview(entryId) {
    return {
        entry: { entry_id: entryId, title: entryId, managed: true },
        generated_at: "2026-11-25T00:00:00+00:00",
    };
}

class FakeApi {
    constructor({
        entries = { entries: [], default_entry_id: null },
        entriesError = null,
        overviewError = null,
    } = {}) {
        this.entriesResponse = entries;
        this.entriesError = entriesError;
        this.overviewError = overviewError;
        this.entryCalls = 0;
        this.overviewCalls = [];
    }

    async entries() {
        this.entryCalls += 1;
        if (this.entriesError) {
            throw this.entriesError;
        }
        return this.entriesResponse;
    }

    async overview(entryId) {
        this.overviewCalls.push(entryId);
        if (this.overviewError) {
            throw this.overviewError;
        }
        return overview(entryId);
    }
}

test("entry_not_found is recognised by the backend error code", () => {
    assert.equal(isEntryNotFound({ code: "entry_not_found" }), true);
    assert.equal(isEntryNotFound({ code: "refresh_failed" }), false);
    assert.equal(isEntryNotFound(new Error("entry_not_found")), false);
    assert.equal(isEntryNotFound(null), false);
    assert.equal(isEntryNotFound("entry_not_found"), false);
});

test("only an entry_not_found outside recovery triggers a reload", () => {
    const missing = { code: "entry_not_found" };
    assert.equal(shouldRecover(missing, false), true);
    assert.equal(shouldRecover(missing, true), false);
    assert.equal(shouldRecover({ code: "internal_error" }, false), false);
});

test("removed selection falls back to the remaining entry", async () => {
    const api = new FakeApi({
        entries: { entries: [entry("b")], default_entry_id: "b" },
    });
    const result = await recoverRemovedEntry(api, "a");

    assert.equal(result.stale, false);
    assert.deepEqual(
        result.entries.map((item) => item.entry_id),
        ["b"],
    );
    assert.equal(result.selected, "b");
    assert.equal(result.overview.entry.entry_id, "b");
    assert.equal(result.error, null);
    assert.equal(api.entryCalls, 1);
    assert.deepEqual(api.overviewCalls, ["b"]);
});

test("removed selection picks a valid entry when several remain", async () => {
    const api = new FakeApi({
        entries: {
            entries: [entry("a"), entry("c")],
            default_entry_id: null,
        },
    });
    const result = await recoverRemovedEntry(api, "b");

    assert.equal(result.stale, false);
    assert.equal(result.selected, "a");
    assert.equal(result.overview.entry.entry_id, "a");
    assert.equal(result.error, null);
});

test("removing the last entry leaves an empty state", async () => {
    const api = new FakeApi({
        entries: { entries: [], default_entry_id: null },
    });
    const result = await recoverRemovedEntry(api, "a");

    assert.equal(result.stale, false);
    assert.deepEqual(result.entries, []);
    assert.equal(result.selected, null);
    assert.equal(result.overview, null);
    assert.equal(result.error, null);
    assert.deepEqual(api.overviewCalls, []);
});

test("a failed entries reload reports a recovery failure", async () => {
    const api = new FakeApi({ entriesError: new Error("offline") });
    const result = await recoverRemovedEntry(api, "a");

    assert.equal(result.stale, false);
    assert.deepEqual(result.entries, []);
    assert.equal(result.selected, null);
    assert.equal(result.overview, null);
    assert.equal(result.error, "recovery_failed");
});

test("a failed overview reload reports a recovery failure without looping", async () => {
    const api = new FakeApi({
        entries: { entries: [entry("b")], default_entry_id: "b" },
        overviewError: new Error("offline"),
    });
    const result = await recoverRemovedEntry(api, "a");

    assert.equal(result.selected, "b");
    assert.equal(result.overview, null);
    assert.equal(result.error, "recovery_failed");
    assert.equal(api.entryCalls, 1);
    assert.deepEqual(api.overviewCalls, ["b"]);
});

test("an entry still listed after entry_not_found does not reload again", async () => {
    const api = new FakeApi({
        entries: {
            entries: [entry("a"), entry("b")],
            default_entry_id: null,
        },
    });
    const result = await recoverRemovedEntry(api, "a");

    assert.equal(result.selected, "a");
    assert.equal(result.overview, null);
    assert.equal(result.error, "recovery_failed");
    assert.equal(api.entryCalls, 1);
    assert.deepEqual(api.overviewCalls, []);
});

test("a single remaining entry is selected from default_entry_id", async () => {
    const api = new FakeApi({
        entries: { entries: [entry("solo")], default_entry_id: "solo" },
    });
    const result = await recoverRemovedEntry(api, "gone");

    assert.equal(result.selected, "solo");
    assert.equal(result.overview.entry.entry_id, "solo");
    assert.equal(result.error, null);
});

test("the recovery is stale when the selection changes during entries()", async () => {
    const api = new FakeApi({
        entries: { entries: [entry("b")], default_entry_id: "b" },
    });
    let current = "a";
    const result = await recoverRemovedEntry(api, "a", () => current === "a");
    current = "b";

    assert.equal(result.stale, false);
    assert.equal(result.selected, "b");

    const stale = await recoverRemovedEntry(api, "a", () => current === "a");
    assert.equal(stale.stale, true);
    assert.deepEqual(stale.entries, []);
    assert.equal(stale.selected, null);
    assert.equal(stale.overview, null);
    assert.equal(stale.error, null);
});

test("the recovery is stale when the selection changes during the overview", async () => {
    const api = new FakeApi({
        entries: { entries: [entry("b")], default_entry_id: "b" },
    });
    let current = "a";
    const result = await recoverRemovedEntry(api, "a", () => {
        if (api.overviewCalls.length > 0) {
            current = "b";
        }
        return current === "a";
    });

    assert.equal(result.stale, true);
    assert.deepEqual(api.overviewCalls, ["b"]);
});

test("a failing reload is stale when the selection changed meanwhile", async () => {
    const api = new FakeApi({ entriesError: new Error("offline") });
    const result = await recoverRemovedEntry(api, "a", () => false);

    assert.equal(result.stale, true);
    assert.equal(result.error, null);
});

test("an omitted isCurrent keeps the recovery always current", async () => {
    const api = new FakeApi({
        entries: { entries: [entry("b")], default_entry_id: "b" },
    });
    const result = await recoverRemovedEntry(api, "a");

    assert.equal(result.stale, false);
    assert.equal(result.selected, "b");
});
