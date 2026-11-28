import type {
    EntriesResponse,
    Overview,
    RefreshResponse,
} from "./types.js";

export interface HaConnection {
    sendMessagePromise<T = unknown>(
        message: Record<string, unknown>,
    ): Promise<T>;
}

export interface HassLike {
    connection: HaConnection;
    language?: string;
}

const PREFIX = "alexa_ma_skill";

export class AlexaMaApi {
    constructor(private readonly hass: HassLike) {}

    entries(): Promise<EntriesResponse> {
        return this.hass.connection.sendMessagePromise<EntriesResponse>({
            type: `${PREFIX}/entries`,
        });
    }

    overview(entryId?: string | null): Promise<Overview> {
        return this.hass.connection.sendMessagePromise<Overview>(
            this.withEntry(`${PREFIX}/overview`, entryId),
        );
    }

    refresh(entryId?: string | null): Promise<RefreshResponse> {
        return this.hass.connection.sendMessagePromise<RefreshResponse>(
            this.withEntry(`${PREFIX}/refresh`, entryId),
        );
    }

    private withEntry(
        type: string,
        entryId?: string | null,
    ): Record<string, unknown> {
        const message: Record<string, unknown> = { type };
        if (entryId) {
            message.entry_id = entryId;
        }
        return message;
    }
}
