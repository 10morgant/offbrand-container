import {
    ActionIcon,
    Center,
    Code,
    CopyButton,
    EmptyState,
    Flex,
    Loader,
    MultiSelect,
    Paper,
    Stack,
    Table,
    Text,
    TextInput,
    Tooltip,
} from "@mantine/core";
import {useMemo, useState} from "react";
import {compareItems, rankItem} from "@tanstack/match-sorter-utils";
import type {Image} from "#/logic/types.ts";
import {
    IconArrowDown,
    IconArrowUp,
    IconCheck,
    IconCopy,
    IconPackage,
    IconSearch,
    IconTerminal,
} from "@tabler/icons-react";
import {colourTheme} from "#/config/colours.ts";
import {formatBytes, formatDate, getUrlString} from "#/logic/utils.ts";
import {PlatformBadges} from "#/components /docker/PlatformBadges.tsx";
import {VariantBadges} from "#/components /docker/VariantBadges.tsx";
import {useRegistryContext} from "#/context/RegistryContext.tsx";

const SHOW_VARIANTS = true
type SortKey = 'tag' | 'version' | 'variant' | 'created';
type SortDirection = 'asc' | 'desc';

interface Props {
    data?: Image;
    loading?: boolean
}

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
    const [sort, setSort] = useState<{ key: SortKey; direction: SortDirection }>({key: 'version', direction: 'desc'});
    const trimmed = search.trim();


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
            .map((image) => ({pkg: image, itemRank: rankItem(image.tag, trimmed)}))
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
    }, [filteredTags, sort]);

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
    }

    return (
        <Paper p="md" radius="md" withBorder style={{overflowX: 'auto'}}>
            <Flex justify={"space-between"} align="flex-end" gap="md" pb={10}>
                <Flex gap="md" align="flex-end" wrap="wrap" style={{flex: 1}}>
                    <TextInput
                        value={search}
                        onChange={(event) => setSearch(event.currentTarget.value)}
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
                        onChange={setVariantsFilter}
                        clearable
                    />
                </Flex>
                <Text> {filteredTags.length}/{data?.tags.length ?? 0} tags</Text>
            </Flex>

            <Table striped highlightOnHover>
                <Table.Thead>
                    <Table.Tr>
                        <Table.Th w={250} onClick={() => handleSort('tag')} style={{cursor: 'pointer'}}>
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
                        {SHOW_VARIANTS && (<Table.Th w={100} onClick={() => handleSort('variant')} style={{cursor: 'pointer'}}>
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
                    {sortedTags.map((tag) => (
                        <Table.Tr key={tag.tag}>
                            <Table.Td>
                                <Tooltip label={tag.tag}>
                                    <Text ff={"monospace"} truncate={"end"}>
                                        {tag.tag}
                                    </Text>
                                </Tooltip>
                            </Table.Td>
                            <Table.Td>
                                <Code>{tag.version ?? '—'}</Code>
                            </Table.Td>
                            {SHOW_VARIANTS && (<Table.Td>
                                <VariantBadges variants={tag.variants ?? []} onclick={(val) => handleVariantTagClick(val)}/>
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
                                    value={`docker pull ${getUrlString(config?.url ?? "http://docker.io")}/${data?.namespace_name??"library"}/${data?.name}:${tag.tag}`}
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
                    ))}
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
            {filteredTags.length < 1 && !loading && (
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

        </Paper>
    )
}