import {EmptyState, Group, Pagination, Select, SimpleGrid, Stack, Text, Title,} from "@mantine/core";
import {IconFolder} from "@tabler/icons-react";
import {Link, useNavigate} from "@tanstack/react-router";
import {useQuery} from "@tanstack/react-query";
import {useEffect, useMemo, useState} from "react";
import {fetchNamespacesOptions} from "#/logic/queries.ts";
import {useRegistryContext} from "#/context/RegistryContext.tsx";
import {SkeletonCard} from "#/components /docker/Cards/SkeletonCard.tsx";
import {NamespaceCard} from "#/components /docker/Cards/NamespaceCard.tsx";
import type {ViewType} from "#/logic/types";

const DEFAULT_PAGE_SIZE = 24;
const NAMESPACES_PAGE_SIZE_KEY = 'namespacesPageSize';

const getStoredPageSize = (fallback: number) => {
    if (typeof window === 'undefined') {
        return fallback;
    }

    const stored = window.localStorage.getItem(NAMESPACES_PAGE_SIZE_KEY);
    if (!stored) {
        return fallback;
    }

    const parsed = Number.parseInt(stored, 10);
    return Number.isFinite(parsed) && parsed > 0 ? parsed : fallback;
};

interface Props {
    initialPageSize?: number;
    cols?: number;
    viewType?: ViewType
    page?: number;
}


export function NamespacesView({initialPageSize = DEFAULT_PAGE_SIZE, cols = 4, viewType = "grid", page: routePage}: Props) {
    const {config} = useRegistryContext()
    const navigate = useNavigate();
    const [pageSize, setPageSize] = useState<number>(() => getStoredPageSize(initialPageSize));
    const [page, setPage] = useState(routePage && routePage > 0 ? routePage : 1);
    const offset = (page - 1) * pageSize;

    useEffect(() => {
        if (typeof window !== 'undefined') {
            window.localStorage.setItem(NAMESPACES_PAGE_SIZE_KEY, pageSize.toString());
        }
    }, [pageSize]);

    useEffect(() => {
        if (routePage && routePage > 0 && routePage !== page) {
            setPage(routePage);
        }
    }, [routePage, page]);

    const {data, isPending, isPlaceholderData} = useQuery({
        ...fetchNamespacesOptions(config?.url ?? "http://example.com", pageSize, offset),
    });

    const namespaces = useMemo(() => data?.items ?? [], [data?.items]);
    const totalPages = data ? Math.max(1, Math.ceil(data.total / pageSize)) : 1;
    const showSkeleton = isPending;

    const handlePageChange = (nextPage: number) => {
        const safePage = Math.max(1, nextPage);
        setPage(safePage);
        navigate({to: safePage === 1 ? '/namespaces/' : `/namespaces/${safePage}`});
    };

    const handlePageSizeChange = (value: string | null) => {
        if (!value) return;
        const nextSize = parseInt(value, 10);
        setPageSize(nextSize);
        setPage(1);
        navigate({to: '/namespaces/'});
    };

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

            {(!data || (data?.total ?? 0) < 1) && !isPending && (
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

            {totalPages > 1 && (
                <Group justify="center">
                    <Pagination total={totalPages} value={page} onChange={handlePageChange}/>
                    <Select
                        placeholder="Page size"
                        data={[10, 20, initialPageSize, 50, 100].map((size) => ({value: size.toString(), label: `${size} per page`}))}
                        value={pageSize.toString()}
                        onChange={handlePageSizeChange}
                    />
                </Group>
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
                    <Pagination total={totalPages} value={page} onChange={handlePageChange}/>
                    <Select
                        placeholder="Page size"
                        data={[10, 20, initialPageSize, 50, 100].map((size) => ({value: size.toString(), label: `${size} per page`}))}
                        value={pageSize.toString()}
                        onChange={handlePageSizeChange}
                    />
                </Group>
            )}
        </Stack>
    );
}