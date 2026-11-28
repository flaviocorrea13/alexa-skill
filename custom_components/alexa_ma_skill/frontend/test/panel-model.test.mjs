import assert from "node:assert/strict";
import test from "node:test";

import { initialView, isBusy, viewFromOverview } from "../.test-build/panel-model.js";

function overview(overrides = {}) {
    return {
        state: "connected",
        stale: false,
        ...overrides,
    };
}

test("initial view is loading", () => {
    const view = initialView();
    assert.equal(view.state, "loading");
    assert.equal(isBusy(view), true);
});

test("missing overview is integration_not_loaded", () => {
    assert.equal(viewFromOverview(null, null).state, "integration_not_loaded");
});

test("connection error is error", () => {
    assert.equal(viewFromOverview(null, "failed").state, "error");
});

test("stale connected data is marked stale", () => {
    const view = viewFromOverview(overview({ stale: true }), null);
    assert.equal(view.state, "stale");
    assert.equal(view.stale, true);
});

test("backend states are preserved", () => {
    for (const state of ["addon_not_found", "addon_stopped", "ma_unavailable", "config_incomplete", "error"]) {
        assert.equal(viewFromOverview(overview({ state }), null).state, state);
    }
});

test("unknown backend state falls back to error", () => {
    assert.equal(viewFromOverview(overview({ state: "unexpected" }), null).state, "error");
});
