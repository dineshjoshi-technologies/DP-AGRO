export const INSECURE_REMOTE_HTTP_ESCAPE_HATCH = "dangerouslyAllowInsecureRemoteHttp";
export function parseBooleanLike(value) {
    if (typeof value === "boolean")
        return value;
    if (typeof value !== "string")
        return null;
    const normalized = value.trim().toLowerCase();
    if (["1", "true", "yes", "on"].includes(normalized))
        return true;
    if (["0", "false", "no", "off"].includes(normalized))
        return false;
    return null;
}
export function isLoopbackHostname(hostname) {
    const value = hostname.toLowerCase().replace(/^\[|\]$/g, "");
    return (value === "localhost" ||
        value === "::1" ||
        value === "0:0:0:0:0:0:0:1" ||
        value === "127.0.0.1" ||
        /^127(?:\.\d{1,3}){3}$/.test(value));
}
export function isRemotePlainHttp(url) {
    return url.protocol === "http:" && !isLoopbackHostname(url.hostname);
}
export function allowsInsecureRemoteHttp(config) {
    return parseBooleanLike(config[INSECURE_REMOTE_HTTP_ESCAPE_HATCH]) === true;
}
export function remotePlainHttpDeniedMessage(hostname) {
    return (`Hermes gateway apiBaseUrl uses remote plain HTTP for "${hostname}". ` +
        `Use HTTPS or set ${INSECURE_REMOTE_HTTP_ESCAPE_HATCH}=true only for unsafe local development.`);
}
//# sourceMappingURL=transport-security.js.map