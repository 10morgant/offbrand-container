export type ViewType = "grid" | "list"

export interface NamespacesRoot {
    total: number
    limit: number
    offset: number
    items: Namespace[]
}

export interface Namespace {
    id: number
    name: string
    num_images: number
    registry: string
    images?: Image[]
}

export interface ImagesRoot {
    total: number
    limit: number
    offset: number
    items: Image[]
}

export interface SearchRoot {
    namespaces: Namespace[]
    images: Image[]
}


export interface Image {
    id: number
    name: string
    self_hosted: boolean
    namespace?: Namespace
    tags: Tag[]
    namespace_name: string
    latest: string
    registry: string
}


export interface Tag {
    id: number
    tag: string
    digest: string,
    size: number
    created_at: string,
    platforms: string[],
}

export interface Stats {
    namespaces: number
    images: number
    tags: number
}

export interface Registry {
    display_name: string
    url: string
    self_hosted: boolean
}

export interface LastUpdated {
    timestamp:string
}
