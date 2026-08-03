import {
    ActionIcon,
    Center,
    CopyButton,
    EmptyState,
    Flex,
    Loader,
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
import {IconCheck, IconCopy, IconPackage, IconSearch} from "@tabler/icons-react";
import {colourTheme} from "#/config/colours.ts";
import {formatBytes, formatDate} from "#/logic/utils.ts";
import {PlatformBadges} from "#/components /docker/PlatformBadges.tsx";


interface Props {
    data?: Image;
    loading?: boolean
}

export function TagView({data, loading = false}: Props) {
    const [search, setSearch] = useState('');
    const trimmed = search.trim();


    const filteredTags = useMemo(() => {
        if (!data || !data.tags) {
            return []
        }
        if (!trimmed) return data.tags;

        const scored = data?.tags
            .map((image) => ({pkg: image, itemRank: rankItem(image.tag, trimmed)}))
            .filter((x) => x.itemRank.passed);
        scored.sort((a, b) => compareItems(a.itemRank, b.itemRank));
        return scored.map((x) => x.pkg);
    }, [trimmed, data]);

    return (
        <Paper p="md" radius="md" withBorder style={{overflowX: 'auto'}}>
            <Flex justify={"space-between"} pb={10}>
                <TextInput
                    value={search}
                    onChange={(event) => setSearch(event.currentTarget.value)}
                    leftSection={loading ? <Loader size={14} color="#2496ED"/> :
                        <IconSearch size={16} color={colourTheme.brand}/>}
                    placeholder={"Search..."}
                    disabled={loading}
                />
                <Text>{data?.tags.length ?? 0} tags</Text>
            </Flex>

            <Table striped highlightOnHover>
                <Table.Thead>
                    <Table.Tr>
                        <Table.Th w={250}>Tag</Table.Th>
                        <Table.Th>Digest</Table.Th>
                        <Table.Th>Platform(s)</Table.Th>
                        <Table.Th>Size</Table.Th>
                        <Table.Th>Created</Table.Th>
                        <Table.Th style={{width: 40}}/>
                    </Table.Tr>
                </Table.Thead>
                <Table.Tbody>
                    {filteredTags.map((tag) => (
                        <Table.Tr key={tag.tag}>
                            <Table.Td>
                                <Tooltip label={tag.tag}>
                                    <Text truncate={"end"}>
                                        {tag.tag}
                                    </Text>
                                </Tooltip>
                            </Table.Td>
                            <Table.Td>
                                <Tooltip label={tag.digest} withArrow>
                                    <Text size="xs" c="dimmed" ff="monospace" style={{cursor: 'default'}}>
                                        {tag.digest !== 'unknown'
                                            ? tag.digest.replace('sha256:', 'sha256:').substring(0, 19) + '…'
                                            : '—'}
                                    </Text>
                                </Tooltip>
                            </Table.Td>
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
                                            position="left"
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