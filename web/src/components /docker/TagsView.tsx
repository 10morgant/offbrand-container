import {
    ActionIcon,
    Center,
    Code,
    CopyButton,
    EmptyState,
    Flex,
    Group,
    Loader,
    MultiSelect,
    Pagination,
    Paper,
    Pill,
    Select,
    Stack,
    Table,
    Text,
    TextInput,
    Tooltip,
} from "@mantine/core";
import {useEffect, useMemo, useState} from "react";
import {compareItems, rankings, rankItem} from "@tanstack/match-sorter-utils";
import type {Image} from "#/logic/types.ts";
import {
    IconArrowDown,
    IconArrowUp,
    IconCheck,
    IconCopy,
    IconFlask,
    IconPackage,
    IconSearch,
    IconTerminal,
} from "@tabler/icons-react";
import {colourTheme} from "#/config/colours.ts";
import {formatBytes, formatDate, getUrlString} from "#/logic/utils.ts";
import {PlatformBadges} from "#/components /docker/PlatformBadges.tsx";
import {platformColorMap, VariantBadges} from "#/components /docker/VariantBadges.tsx";
import {useRegistryContext} from "#/context/RegistryContext.tsx";
import {isPreRelease} from "#/logic/version.ts";

const SHOW_VARIANTS = true
const DEFAULT_PAGE_SIZE = 100;
const PAGE_SIZE_OPTIONS = [25, 50, DEFAULT_PAGE_SIZE, 150, 200, 300, 500, 1000];
type SortKey = 'tag' | 'version' | 'variant' | 'created';
type SortDirection = 'asc' | 'desc';

interface Props {
    data?: Image;
    loading?: boolean
}

const getPageSizeFromUrl = () => {
    if (typeof window === 'undefined') {
        return DEFAULT_PAGE_SIZE;
    }

    const params = new URLSearchParams(window.location.search);
    const rawValue = params.get('page_size');
    const parsed = rawValue === null ? NaN : Number.parseInt(rawValue, 10);
    return Number.isFinite(parsed) && parsed > 0 ? parsed : DEFAULT_PAGE_SIZE;
};

const getSortIcon = (isActive: boolean, direction: SortDirection) => {
    if (!isActive) return null;
    return direction === 'asc' ? <IconArrowUp size={14}/> : <IconArrowDown size={14}/>;
};

const compareVersions = (left: string, right: string): number => {
    return left.localeCompare(right, undefined, {numeric: true, sensitivity: 'base'});
};

export function TagView({data, loading = false}: Props) {
    const {config} = useRegistryContext()
    const [search, setSearch] = useState('');
    const [variantsFilter, setVariantsFilter] = useState<string[]>([]);
    const [pageSize, setPageSize] = useState<number>(() => getPageSizeFromUrl());
    const [page, setPage] = useState(1);
    const [sort, setSort] = useState<{ key: SortKey; direction: SortDirection }>({key: 'version', direction: 'desc'});
    const trimmed = search.trim();

    useEffect(() => {
        if (typeof window === 'undefined') {
            return;
        }

        const nextUrl = new URL(window.location.href);
        if (pageSize === DEFAULT_PAGE_SIZE) {
            nextUrl.searchParams.delete('page_size');
        } else {
            nextUrl.searchParams.set('page_size', pageSize.toString());
        }

        const nextSearch = `${nextUrl.pathname}${nextUrl.search}`;
        if (window.location.pathname + window.location.search !== nextSearch) {
            window.history.replaceState({}, '', nextSearch);
        }
    }, [pageSize]);

    const filteredTags = useMemo(() => {
        if (!data || !data.tags) {
            return []
        }

        const filteredByVariant = data.tags.filter(tag => {
            if (variantsFilter.length === 0) {
                return true;
            }
            return tag.variants?.some(variant => variantsFilter.includes(variant)) ?? false;
        });

        if (!trimmed) return filteredByVariant;

        const scored = filteredByVariant
            .map((image) => ({pkg: image, itemRank: rankItem(image.tag, trimmed, {threshold: rankings.WORD_STARTS_WITH})}))
            .filter((x) => x.itemRank.passed);
        scored.sort((a, b) => compareItems(a.itemRank, b.itemRank));
        return scored.map((x) => x.pkg);
    }, [trimmed, data, variantsFilter]);

    const variants = useMemo(() => {
        if (!data || !data.tags) {
            return []
        }
        const variantSet = new Set<string>();
        data.tags.forEach(tag => {
            tag.variants?.forEach(variant => {
                variantSet.add(variant);
            });
        });
        return Array.from(variantSet).map(variant => ({value: variant, label: variant}));
    }, [data]);

    const sortedTags = useMemo(() => {
        const items = [...filteredTags];

        items.sort((left, right) => {
            const directionMultiplier = sort.direction === 'asc' ? 1 : -1;

            switch (sort.key) {
                case 'tag':
                    return compareVersions(left.tag, right.tag) * directionMultiplier;
                case 'version': {
                    const leftVersion = left.version ?? '';
                    const rightVersion = right.version ?? '';
                    return compareVersions(leftVersion, rightVersion) * directionMultiplier;
                }
                case 'variant': {
                    const leftVariant = (left.variants ?? []).join(', ').toLowerCase();
                    const rightVariant = (right.variants ?? []).join(', ').toLowerCase();
                    return leftVariant.localeCompare(rightVariant) * directionMultiplier;
                }
                case 'created': {
                    const leftDate = new Date(left.created_at).getTime();
                    const rightDate = new Date(right.created_at).getTime();
                    return (leftDate - rightDate) * directionMultiplier;
                }
                default:
                    return 0;
            }
        });

        return items;
    }, [filteredTags, sort.direction, sort.key]);

    const totalPages = Math.max(1, Math.ceil(sortedTags.length / pageSize));
    const safePage = Math.min(Math.max(page, 1), totalPages);

    useEffect(() => {
        setPage((current) => Math.min(current, totalPages));
    }, [totalPages]);

    const paginatedTags = useMemo(() => {
        const startIndex = (safePage - 1) * pageSize;
        return sortedTags.slice(startIndex, startIndex + pageSize);
    }, [pageSize, safePage, sortedTags]);

    const handleSort = (key: SortKey) => {
        setSort((current) => {
            if (current.key === key) {
                return {
                    key,
                    direction: current.direction === 'asc' ? 'desc' : 'asc',
                };
            }

            return {
                key,
                direction: key === 'created' ? 'desc' : 'asc',
            };
        });
    };

    const handleVariantTagClick = (variant: string) => {
        setVariantsFilter((current) => {
            if (current.includes(variant)) {
                return current.filter((v) => v !== variant);
            } else {
                return [...current, variant];
            }
        });
        setPage(1);
    }

    const handlePageSizeChange = (value: string | null) => {
        if (!value) {
            return;
        }

        const parsed = Number.parseInt(value, 10);
        if (!Number.isFinite(parsed) || parsed <= 0) {
            return;
        }

        setPageSize(parsed);
        setPage(1);
    };

    return (
        <Paper p="md" radius="md" withBorder style={{overflowX: 'auto'}}>
            <Flex justify={"space-between"} align="flex-end" gap="md" pb={10}>
                <Flex gap="md" align="flex-end" wrap="wrap" style={{flex: 1}}>
                    <TextInput
                        value={search}
                        onChange={(event) => {
                            setSearch(event.currentTarget.value);
                            setPage(1);
                        }}
                        leftSection={loading ? <Loader size={14} color="#2496ED"/> :
                            <IconSearch size={16} color={colourTheme.brand}/>}
                        placeholder={"Search..."}
                        disabled={loading}
                    />
                    <MultiSelect
                        label="Variant"
                        placeholder="Pick value"
                        data={variants}
                        value={variantsFilter}
                        onChange={(value) => {
                            setVariantsFilter(value);
                            setPage(1);
                        }}
                        clearable

                        renderPill={({option, onRemove}) => {
                            return (
                                <Pill withRemoveButton onRemove={onRemove}
                                      bg={platformColorMap[option?.value.toString()] ?? 'gray'}
                                      c={"white"}
                                      fw={800}
                                      tt={"uppercase"}
                                >
                                    {option?.label}
                                </Pill>
                            );
                        }}
                    />
                </Flex>
                <Text> {filteredTags.length}/{data?.tags.length ?? 0} tags</Text>
            </Flex>

            <Group justify="space-between" align="center" mt="xs" mb="md">
                <Text size="sm" c="dimmed">
                    Showing {paginatedTags.length > 0 ? (safePage - 1) * pageSize + 1 : 0}-{Math.min(safePage * pageSize, sortedTags.length)} of {sortedTags.length} tags
                </Text>
                <Select
                    value={pageSize.toString()}
                    onChange={handlePageSizeChange}
                    data={PAGE_SIZE_OPTIONS.map((size) => ({value: size.toString(), label: `${size} per page`}))}
                    placeholder="Page size"
                    allowDeselect={false}
                    w={150}
                />
            </Group>

            {sortedTags.length > 1 && (
                <Group justify="center" mb="md">
                    <Pagination total={totalPages} value={safePage} onChange={setPage} size="sm"/>
                </Group>
            )}

            <Table striped highlightOnHover>
                <Table.Thead>
                    <Table.Tr>
                        <Table.Th w={350} onClick={() => handleSort('tag')} style={{cursor: 'pointer'}}>
                            <Flex align="center" gap={4}>
                                <Text>Tag</Text>
                                {getSortIcon(sort.key === 'tag', sort.direction)}
                            </Flex>
                        </Table.Th>
                        <Table.Th w={100} onClick={() => handleSort('version')} style={{cursor: 'pointer'}}>
                            <Flex align="center" gap={4}>
                                <Text>Version</Text>
                                {getSortIcon(sort.key === 'version', sort.direction)}
                            </Flex>
                        </Table.Th>
                        {SHOW_VARIANTS && (
                            <Table.Th w={100} onClick={() => handleSort('variant')} style={{cursor: 'pointer'}}>
                                <Flex align="center" gap={4}>
                                    <Text>Variant</Text>
                                    {getSortIcon(sort.key === 'variant', sort.direction)}
                                </Flex>
                            </Table.Th>)}
                        {/*<Table.Th>Digest</Table.Th>*/}
                        <Table.Th>Platform(s)</Table.Th>
                        <Table.Th>Size</Table.Th>
                        <Table.Th onClick={() => handleSort('created')} style={{cursor: 'pointer'}}>
                            <Flex align="center" gap={4}>
                                <Text>Created</Text>
                                {getSortIcon(sort.key === 'created', sort.direction)}
                            </Flex>
                        </Table.Th>
                        <Table.Th w={80}/>
                    </Table.Tr>
                </Table.Thead>
                <Table.Tbody>
                    {paginatedTags.map((tag) => {
                        const pre = isPreRelease(tag.version ?? "")
                        return (
                            <Table.Tr key={`${tag.tag}-${tag.digest}`}>
                                <Table.Td>
                                    <Group>
                                        <Tooltip label={tag.tag}>
                                            <Text ff={"monospace"} truncate={"end"}>
                                                {tag.tag}
                                            </Text>
                                        </Tooltip>
                                        <Tooltip label={"Pre-release version"} withArrow>
                                            <div>
                                                {pre && <IconFlask size={18} color={"gray"}/>}
                                            </div>
                                        </Tooltip>
                                    </Group>
                                </Table.Td>
                                <Table.Td>
                                    <Code>{tag.version ?? '—'}</Code>
                                </Table.Td>
                                {SHOW_VARIANTS && (<Table.Td>
                                    <VariantBadges variants={tag.variants ?? []}
                                                   onclick={(val) => handleVariantTagClick(val)}/>
                                </Table.Td>)}
                                {/*<Table.Td>
                                <Tooltip label={tag.digest} withArrow>
                                    <Text size="xs" c="dimmed" ff="monospace" style={{cursor: 'default'}}>
                                        {tag.digest !== 'unknown'
                                            ? tag.digest.replace('sha256:', 'sha256:').substring(0, 19) + '…'
                                            : '—'}
                                    </Text>
                                </Tooltip>
                            </Table.Td>*/}
                                <Table.Td>
                                    <PlatformBadges platforms={tag.platforms}/>
                                </Table.Td>
                                <Table.Td>
                                    <Text size="sm">{formatBytes(tag.size)}</Text>
                                </Table.Td>
                                <Table.Td>
                                    <Text size="xs" c="dimmed">
                                        {formatDate(tag.created_at)}
                                    </Text>
                                </Table.Td>
                                <Table.Td>
                                    <CopyButton value={`${data?.name}:${tag.tag}`} timeout={2000}>
                                        {({copied, copy}) => (
                                            <Tooltip
                                                label={copied ? 'Copied!' : 'Copy name and tag'}
                                                withArrow
                                                position="top"
                                            >
                                                <ActionIcon
                                                    color={copied ? 'teal' : 'gray'}
                                                    variant="subtle"
                                                    onClick={copy}
                                                    size="sm"
                                                >
                                                    {copied ? <IconCheck size={16}/> : <IconCopy size={16}/>}
                                                </ActionIcon>
                                            </Tooltip>
                                        )}
                                    </CopyButton>
                                    <CopyButton
                                        value={`docker pull ${getUrlString(config?.url ?? "http://docker.io")}/${data?.namespace_name ?? "library"}/${data?.name}:${tag.tag}`}
                                        timeout={2000}
                                    >
                                        {({copied, copy}) => (
                                            <Tooltip
                                                label={copied ? 'Copied!' : 'Copy command'}
                                                withArrow
                                                position="top"
                                            >
                                                <ActionIcon
                                                    color={copied ? 'teal' : 'gray'}
                                                    variant="subtle"
                                                    onClick={copy}
                                                    size="sm"
                                                >
                                                    {copied ? <IconCheck size={16}/> : <IconTerminal size={16}/>}
                                                </ActionIcon>
                                            </Tooltip>
                                        )}
                                    </CopyButton>
                                </Table.Td>
                            </Table.Tr>
                        )
                    })}
                </Table.Tbody>

            </Table>
            {loading && (
                <Center p={40}>
                    <Stack align={"center"}>
                        <Loader color="#2496ED"/>
                        <Text>Loading...</Text>
                    </Stack>
                </Center>
            )}
            {sortedTags.length < 1 && !loading && (
                <EmptyState
                    withIndicatorBackground
                    icon={<IconPackage/>}
                    title="No tags found"
                    pt={40}
                    pb={40}
                >
                    <EmptyState.Description>
                        There are no tags for this image available right now.

                    </EmptyState.Description>
                    <EmptyState.Actions>
                        {/*<Button variant="default">Refresh</Button>*/}
                    </EmptyState.Actions>
                </EmptyState>
            )}

            {sortedTags.length > 1 && (
                <Group justify="center" mt="md">
                    <Pagination total={totalPages} value={safePage} onChange={setPage} size="sm"/>
                </Group>
            )}

        </Paper>
    )
}