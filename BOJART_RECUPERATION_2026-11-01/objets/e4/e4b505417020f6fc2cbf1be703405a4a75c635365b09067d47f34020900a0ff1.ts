import type { FontStackRef } from "@hypit/media";
import type { Timeline } from "@hypit/timeline";
import type { SpatialFrame } from "@hypit/spatial";
import type { TemporalInstant, TemporalWindow } from "@hypit/temporal";
export type Message = {
    id: string;
    sender: string;
    text: string;
    side: "left" | "right";
    at: TemporalInstant;
};
export type ChatOptions = {
    id: string;
    title: string;
    entranceFrames: number;
};
/** Layout, arrival and scrolling share one visual component; timing is already resolved. */
export declare function renderChat(timeline: Timeline, within: SpatialFrame, window: TemporalWindow, font: FontStackRef, messages: readonly Message[], options: ChatOptions): import("@hypit/composition").VisualTrack;
