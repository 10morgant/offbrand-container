type UrlParams = Record<string, string | number | boolean | undefined | null>;

export function buildUrl(base: string, params?: UrlParams): string {
    const url = new URL(base, window.location.origin);
    if (params) {
        Object.entries(params).forEach(([key, value]) => {
            if (value !== undefined && value !== null) {
                url.searchParams.append(key, String(value));
            }
        });
    }
    return url.toString();
}

export function getUrlString(url: string) {
    const u = new URL(url)
    return url.replace(`${u.protocol}//`, "")
}

export function formatBytes(bytes: number): string {
    if (bytes === 0) return '—'
    const k = 1024
    const sizes = ['B', 'KB', 'MB', 'GB']
    const i = Math.floor(Math.log(bytes) / Math.log(k))
    return Math.round((bytes / Math.pow(k, i)) * 100) / 100 + ' ' + sizes[i]
}

export function formatDate(iso: string | null): string {
    if (!iso) return '—'
    try {
        return new Intl.DateTimeFormat(undefined, {
            year: 'numeric',
            month: 'short',
            day: 'numeric',
            hour: '2-digit',
            minute: '2-digit',
        }).format(new Date(iso))
    } catch {
        return iso
    }
}