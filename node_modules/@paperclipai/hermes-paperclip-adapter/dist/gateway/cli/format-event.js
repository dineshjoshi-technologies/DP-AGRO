export function printHermesGatewayStreamEvent(line, debug) {
    const trimmed = line.trim();
    if (!trimmed)
        return;
    if (trimmed.startsWith("[hermes-gateway:event]")) {
        console.log(trimmed);
        return;
    }
    if (trimmed.startsWith("[hermes-gateway]")) {
        console.log(trimmed);
        return;
    }
    if (debug)
        console.log(line);
}
//# sourceMappingURL=format-event.js.map