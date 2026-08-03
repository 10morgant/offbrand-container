import {EmptyState, Group, Pagination, SimpleGrid, Stack, Text, Title,} from "@mantine/core";
import {IconFolder} from "@tabler/icons-react";
import {Link} from "@tanstack/react-router";
import {useQuery} from "@tanstack/react-query";
import {useMemo, useState} from "react";
import {fetchNamespacesOptions} from "#/logic/queries.ts";
import {useRegistryContext} from "#/context/RegistryContext.tsx";
import {SkeletonCard} from "#/components /docker/Cards/SkeletonCard.tsx";
import {NamespaceCard} from "#/components /docker/Cards/NamespaceCard.tsx";
import type { ViewType } from "#/logic/types";

const DEFAULT_PAGE_SIZE = 24;


interface Props {
    pageSize?: number;
    cols?: number;
    viewType?: ViewType
}


export function NamespacesView({pageSize = DEFAULT_PAGE_SIZE, cols=4, viewType = "grid"}: Props) {
    const {config} = useRegistryContext()
    const [page, setPage] = useState(1);
    const offset = (page - 1) * pageSize;

    const {data, isPending, isPlaceholderData} = useQuery({
        ...fetchNamespacesOptions(config?.url ?? "http://example.com", pageSize, offset),
    });

    const namespaces = useMemo(() => data?.items ?? [], [data?.items]);
    const totalPages = data ? Math.max(1, Math.ceil(data.total / pageSize)) : 1;
    const showSkeleton = isPending;

    return (
        <Stack gap="md">
            <Group
                justify="space-between"
                component={Link}
                // @ts-ignore
                to={"/namespaces/"}
            >
                <Title order={4}>Namespaces</Title>
                <Text size="sm" c="dimmed">
                    {showSkeleton
                        ? "..."
                        : `${namespaces.length}/${data?.total ?? 0} namespace${data?.total !== 1 ? "s" : ""}`}
                </Text>
            </Group>

            {(!data || (data?.total?? 0) < 1) && !isPending && (
                <EmptyState
                    withIndicatorBackground
                    icon={<IconFolder color="var(--mantine-color-yellow-4)"/>}
                    title="No namespaces found"
                >
                    <EmptyState.Description>
                        There are no docker namespaces available right now.

                    </EmptyState.Description>
                    <EmptyState.Actions>
                        {/*<Button variant="default">Refresh</Button>*/}
                    </EmptyState.Actions>
                </EmptyState>
            )}

            {viewType === "grid" && (
                <SimpleGrid
                    cols={{base: 2, sm: cols}}
                    spacing="sm"
                    style={{opacity: isPlaceholderData ? 0.6 : 1, transition: "opacity 150ms ease"}}
                >
                    {showSkeleton
                        ? Array.from({length: cols}).map((_, i) => <SkeletonCard key={i}/>)
                        : namespaces.map((ns, i) => (
                            <NamespaceCard key={i} ns={ns}/>
                        ))}
                </SimpleGrid>
            )}

            {viewType === "list" && (
                <Stack
                    gap="sm"
                    style={{opacity: isPlaceholderData ? 0.6 : 1, transition: "opacity 150ms ease"}}
                >
                    {showSkeleton
                        ? Array.from({length: cols}).map((_, i) => <SkeletonCard key={i}/>)
                        : namespaces.map((ns, i) => (
                            <NamespaceCard key={i} ns={ns}/>
                        ))}
                </Stack>
            )}


            {totalPages > 1 && (
                <Group justify="center">
                    <Pagination total={totalPages} value={page} onChange={setPage}/>
                </Group>
            )}
        </Stack>
    );
}