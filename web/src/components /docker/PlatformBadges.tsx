import {Badge, Flex, HoverCard, ScrollArea, Stack} from "@mantine/core";


export interface PlatformBadgesProps {
    platforms: string[]
    maxDisplay?: number
}

export interface PlatformBadgeProps {
    val: string
}

const platformColorMap: Record<string, string> = {
    "windows/amd64": "purple",
    "linux/amd64": "orange",
    "linux/386": "cyan",
    "linux/arm64": "green",
    "linux/arm64/v8": "green",
    "linux/arm/v5": "lime",
    "linux/arm/v6": "lime",
    "linux/arm/v7": "lime",
    "linux/ppc64le": "grape",
    "linux/mips64le": "pink",
    "linux/riscv64": "teal",
    "linux/s390x": "red",
}

export function PlatformBadge({val}: PlatformBadgeProps) {
    const color = platformColorMap[val] ?? "gray"
    return (
        <Badge color={color}>
            {val}
        </Badge>
    )
}

export function PlatformBadges({platforms, maxDisplay = 4}: PlatformBadgesProps) {
    return (
        <Flex w={250} wrap={"wrap"} gap={4}>
            {platforms.slice(0, maxDisplay).map((platform) => (
                <PlatformBadge val={platform}/>
            ))}
            {platforms.length > maxDisplay && (
                <HoverCard shadow="md">
                    <HoverCard.Target>
                        <Badge>+ {platforms.length - maxDisplay}</Badge>
                    </HoverCard.Target>
                    <HoverCard.Dropdown>
                        <ScrollArea h={250}>
                            <Stack>
                                {platforms.map((platform) => (
                                    <PlatformBadge val={platform}/>
                                ))}
                            </Stack>
                        </ScrollArea>
                    </HoverCard.Dropdown>
                </HoverCard>

            )}
        </Flex>
    );
}