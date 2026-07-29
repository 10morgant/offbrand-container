import {type Icon, IconBrandDocker} from "@tabler/icons-react";


export interface App {
    name: string
    url: string
    icon: Icon
    color: string
}

export const APPS: App[] = [
    {
        name: "Offbrand Container",
        url: "http://localhost:8000",
        color: "#2560FF",
        icon: IconBrandDocker
    }
]