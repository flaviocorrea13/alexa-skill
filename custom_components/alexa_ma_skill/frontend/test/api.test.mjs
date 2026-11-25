import assert from "node:assert/strict";
import test from "node:test";

import { AlexaMaApi } from "../.test-build/api.js";

class FakeConnection {
    constructor() {
        this.messages = [];
        this.responses = [];
    }

    async sendMessagePromise(message) {
        this.messages.push(message);
        return this.responses.shift();
    }
}

function hassWith(connection) {
    return { connection, language: "pt-BR" };
}

test("entries sends the expected command", async () => {
    const connection = new FakeConnection();
    connection.responses.push({ entries: [], default_entry_id: null });
    const api = new AlexaMaApi(hassWith(connection));
    await api.entries();
    assert.deepEqual(connection.messages, [{ type: "alexa_ma_skill/entries" }]);
});

test("overview includes entry_id only when provided", async () => {
    const connection = new FakeConnection();
    connection.responses.push({}, {});
    const api = new AlexaMaApi(hassWith(connection));
    await api.overview();
    await api.overview("entry-1");
    assert.deepEqual(connection.messages, [
        { type: "alexa_ma_skill/overview" },
        { type: "alexa_ma_skill/overview", entry_id: "entry-1" },
    ]);
});

test("refresh sends the expected command", async () => {
    const connection = new FakeConnection();
    connection.responses.push({ success: true, refreshed: true, overview: {} });
    const api = new AlexaMaApi(hassWith(connection));
    await api.refresh("entry-1");
    assert.deepEqual(connection.messages, [
        { type: "alexa_ma_skill/refresh", entry_id: "entry-1" },
    ]);
});

test("websocket failure propagates to the caller", async () => {
    const connection = {
        async sendMessagePromise() {
            throw new Error("unauthorized");
        },
    };
    const api = new AlexaMaApi(hassWith(connection));
    await assert.rejects(() => api.entries(), /unauthorized/);
});
