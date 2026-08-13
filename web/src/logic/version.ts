import semver from "semver";

export function isPreRelease(version: string): boolean {
    if (typeof version !== "string") {
        return false;
    }

    const trimmed = version.trim();
    if (!trimmed) {
        return false;
    }

    const parsed = semver.parse(trimmed, {loose: true}) ?? semver.coerce(trimmed);
    return !!parsed && parsed.prerelease.length > 0;
}