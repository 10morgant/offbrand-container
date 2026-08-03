import {Badge, Flex, HoverCard, ScrollArea, Stack} from "@mantine/core";


export interface VariantBadgesProps {
    variants: string[]
    maxDisplay?: number
}

export interface VariantBadgeProps {
    val: string
}

const platformColorMap: Record<string, string> = {
    "bookworm": "purple",
    "bullseye": "purple",
    "buster": "purple",
    "slim": "orange",
    "alpine": "cyan",
    "beta": "green",
    "alpha": "lime",
    "rc": "grape",
    "linux/mips64le": "pink",
    "linux/riscv64": "teal",
    "linux/s390x": "red",
}

export function VariantBadge({val}: VariantBadgeProps) {
    const color = platformColorMap[val] ?? "gray"
    return (
        <Badge color={color} variant={""}>
            {val}
        </Badge>
    )
}

export function VariantBadges({variants, maxDisplay = 4}: VariantBadgesProps) {
    return (
        <Flex w={250} wrap={"wrap"} gap={4}>
            {variants.slice(0, maxDisplay).map((platform) => (
                <VariantBadge val={platform}/>
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
                                    <VariantBadge val={platform}/>
                                ))}
                            </Stack>
                        </ScrollArea>
                    </HoverCard.Dropdown>
                </HoverCard>

            )}
        </Flex>
    );
}