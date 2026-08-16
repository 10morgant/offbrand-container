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

export function getLatestVersionNumber(versions: string[]): string | null {
    if (!Array.isArray(versions) || versions.length === 0) {
        return null;
    }

    const validVersions = versions
        .map((v) => semver.parse(v, {loose: true}) ?? semver.coerce(v))
        .filter((v): v is semver.SemVer => v !== null);

    if (validVersions.length === 0) {
        return null;
    }

    const latestVersion = validVersions.reduce((latest, current) => {
        return semver.gt(current, latest) ? current : latest;
    });

    return latestVersion.format();
}