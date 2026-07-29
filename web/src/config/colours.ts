export interface ColourTheme {
    brand: string
    brand_dark: string
    hero_top: string
    hero_body: string
    page: string
    surface: string
    surface_2: string
}

const brand = "#2560ff"
// const brand = "#3d0a0a"

export const colourTheme: ColourTheme = {
    // navbar: 'var(--mantine-color-theme-9)',
    // hero: 'var(--mantine-color-theme-8)',
    // hero_span: 'var(--mantine-color-theme-5)',
    // #2560ff #00153C
    brand:brand,
    hero_body: `color-mix(in srgb, ${brand} 65%, black)`,
    hero_top: `color-mix(in srgb, ${brand} 18%, #050816)`,
    brand_dark: `color-mix(in srgb, ${brand} 10%, #050816 )`,
    page: `color-mix(in srgb, ${brand} 3%, #050816 )`,
    surface: `color-mix(in srgb, ${brand} 5%, #0b1020 )`,
    surface_2: `color-mix(in srgb, ${brand} 8%, #111827 )`,
}
/* oklab(48%, 35%, 16.5%) srgb(163,45,45)
    brand: "#e24b4a",
    brand_dark: "#a32d2d",
    hero_top: "#3d0a0a",
    hero_body: "#5c1010",
    page: "#0f0a0a",
    surface: "#1a0e0e",
    surface_2: "#2a1212",

 */