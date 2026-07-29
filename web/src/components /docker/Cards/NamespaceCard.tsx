import {Card, Group, Text} from "@mantine/core";
import {Link} from "@tanstack/react-router";
import {IconFolder, IconFolderOpen} from "@tabler/icons-react";
import type {Namespace} from "#/logic/types.ts";

export function NamespaceCard({ns}: { ns: Namespace }) {
    return (
        <Card
            p="sm"
            radius="md"
            withBorder
            style={{cursor: "pointer", height: "100%"}}
            component={Link}
            to={"/$namespace"}
            // @ts-expect-error expected
            params={{namespace: ns.name}}
        >
            <Group gap="xs" mb={6}>
                {ns.name === "_" ? (
                    <IconFolderOpen size={18} color="var(--mantine-color-yellow-4)"/>
                ) : (
                    <IconFolder size={18} color="var(--mantine-color-yellow-4)"/>
                )}
                <Text fw={600} size="sm" truncate style={{flex: 1}}>
                    {ns.name}
                </Text>
            </Group>
        </Card>
    )
}