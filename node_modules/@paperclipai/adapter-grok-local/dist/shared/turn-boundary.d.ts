export interface TurnBoundaryState {
    lastChunk: string;
    backtickParity: 0 | 1;
}
export declare function createTurnBoundaryState(): TurnBoundaryState;
export declare function applyTurnBoundary(state: TurnBoundaryState, incoming: string): string;
//# sourceMappingURL=turn-boundary.d.ts.map