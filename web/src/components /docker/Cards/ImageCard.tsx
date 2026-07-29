import {Card, Flex, Group, Stack, Text, Title} from "@mantine/core";
import {Link} from "@tanstack/react-router";
import {IconBrandDocker} from "@tabler/icons-react";
import type {Image} from "#/logic/types.ts";

export function ImageCard({image}: { image: Image }) {
    return (
        <Card
            p="sm"
            radius="md"
            withBorder
            style={{cursor: "pointer", height: "100%"}}
            component={Link}
            to={"/$namespace/$image"}
            // @ts-expect-error expected
            params={{namespace: image.namespace_name, image: image.name}}
        >
            <Group gap="xs" mb={6}>

                <IconBrandDocker size={18} color="var(--mantine-color-blue-4)"/>
                <Stack gap={0}>
                    <Text c={"dimmed"}>{image.namespace_name}/</Text>
                    <Flex justify={"space-between"}>
                        <Title order={4} fw={600}>
                            {image.name}
                        </Title>
                    </Flex>

                </Stack>
            </Group>
        </Card>
    )
}