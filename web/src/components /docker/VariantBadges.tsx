import {Badge, Flex, HoverCard, ScrollArea, Stack} from "@mantine/core";


export interface VariantBadgesProps {
    variants: string[]
    maxDisplay?: number
    onclick: (variant: string) => void
}

export interface VariantBadgeProps {
    val: string
    onclick: (variant: string) => void
}

export const platformColorMap: Record<string, string> = {
    "bookworm": "#D70A53",
    "bullseye": "#D70A53",
    "buster": "#D70A53",
    "trixie": "#D70A53",
    "debian": "#D70A53",
    "slim": "yellow",
    "alpine": "#0D597F",
    "alpine3.20": "#0D597F",
    "alpine3.21": "#0D597F",
    "alpine3.22": "#0D597F",
    "alpine3.23": "#0D597F",
    "alpine3.24": "#0D597F",
    "beta": "green",
    "alpha": "lime",
    "rc": "grape",
    "linux/mips64le": "pink",
    "linux/riscv64": "teal",
    "linux/s390x": "red",
    "windowsservercore": "#800080",
    "ltsc2022": "#800080",
    "ltsc2023": "#800080",
    "ltsc2024": "#800080",
    "ltsc2025": "#800080",
    "ltsc2026": "#800080",
}

export function VariantBadge({val, onclick}: VariantBadgeProps) {
    const color = platformColorMap[val] ?? "gray"
    return (
        <Badge
            color={color}
            variant={"dot"}
            onClick={() => onclick(val)} style={{cursor: "pointer"}}

        >
            {val}
        </Badge>
    )
}

export function VariantBadges({variants, onclick, maxDisplay = 4}: VariantBadgesProps) {
    return (
        <Flex w={200} wrap={"wrap"} gap={4}>
            {variants.slice(0, maxDisplay).map((platform, i) => (
                <VariantBadge val={platform} key={i} onclick={onclick}/>
            ))}
            {variants.length > maxDisplay && (
                <HoverCard shadow="md">
                    <HoverCard.Target>
                        <Badge>+ {variants.length - maxDisplay}</Badge>
                    </HoverCard.Target>
                    <HoverCard.Dropdown>
                        <ScrollArea h={250}>
                            <Stack>
                                {variants.map((platform) => (
                                    <VariantBadge val={platform} onclick={onclick}/>
                                ))}
                            </Stack>
                        </ScrollArea>
                    </HoverCard.Dropdown>
                </HoverCard>

            )}
        </Flex>
    );
}