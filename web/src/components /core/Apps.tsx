import {Card, HoverCard, SimpleGrid, Stack, Text, ThemeIcon, Title} from "@mantine/core";
import {IconGridDots} from "@tabler/icons-react";
import {APPS} from "#/config/apps.tsx";
import {Link} from "@tanstack/react-router";

export function Apps() {
    return (
        <HoverCard width={"auto"} shadow="md" withArrow openDelay={200} closeDelay={400}>
            <HoverCard.Target>
                <IconGridDots/>
            </HoverCard.Target>
            <HoverCard.Dropdown>
                <Title order={6} tt="uppercase" pb={5}>
                    Other Apps
                </Title>
                <SimpleGrid cols={3}>
                    {APPS.map((app) => (
                        <Card w={140} bg={"gray"}>
                            <Link to={app.url}>
                                <Stack align={"center"}>
                                    <ThemeIcon variant={"light"} color={app.color} size={"lg"}>
                                        <app.icon size={42}/>
                                    </ThemeIcon>
                                    <Text fz={10}>{app.name}</Text>
                                </Stack>
                            </Link>
                        </Card>
                    ))}
                </SimpleGrid>
            </HoverCard.Dropdown>
        </HoverCard>
    );
}