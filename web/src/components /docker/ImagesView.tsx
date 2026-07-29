import {
    EmptyState,
    Flex,
    Group,
    Loader,
    SegmentedControl,
    SimpleGrid,
    Stack,
    Text,
    TextInput,
    Title,
} from "@mantine/core";
import {useMemo, useState} from "react";
import {compareItems, rankItem} from "@tanstack/match-sorter-utils";
import type {Image, Namespace} from "#/logic/types.ts";
import {ImageCard} from "#/components /docker/Cards/ImageCard.tsx";
import {IconPackage, IconSearch} from "@tabler/icons-react";
import {colourTheme} from "#/config/colours.ts";
import {SkeletonCard} from "#/components /docker/Cards/SkeletonCard.tsx";


type ViewType = "grid" | "list"

interface Props {
    data?: Namespace;
    viewType?: ViewType
    loading?: boolean
    showSearch?: boolean
    images?: Image[]
    cols?: number
    total?: number
}

export function ImagesView({
                               data,
                               images,
                               total,
                               cols = 3,
                               viewType = "grid",
                               loading = false,
                               showSearch = true
                           }: Props) {
    const [search, setSearch] = useState('');
    const [view, setView] = useState(viewType);
    const trimmed = search.trim();
    const ims = (data?.images ?? images) ?? []
    const totalIms = (data?.num_images ?? total) ?? 0


    const filteredimages = useMemo(() => {
        if (!ims) {
            return []
        }
        if (!trimmed) return ims;

        const scored = ims
            .map((image) => ({pkg: image, itemRank: rankItem(image.name, trimmed)}))
            .filter((x) => x.itemRank.passed);
        scored.sort((a, b) => compareItems(a.itemRank, b.itemRank));
        return scored.map((x) => x.pkg);
    }, [trimmed, ims]);

    return (
        <Stack>
            <Group justify="space-between">
                <Title order={4}>Images</Title>
                <Text size="sm" c="dimmed">
                    {loading
                        ? "..."
                        : `${ims.length}/${totalIms ?? 0} image${totalIms !== 1 ? "s" : ""}`}
                </Text>
            </Group>
            {/*<Container size={1200} pt={40} pb={40}>*/}
            {showSearch && (<Flex justify={"space-between"} pb={10}>
                <TextInput
                    value={search}
                    onChange={(event) => setSearch(event.currentTarget.value)}
                    leftSection={loading ? <Loader size={14} color="#2496ED"/> :
                        <IconSearch size={16} color={colourTheme.brand}/>}
                    placeholder={"Search..."}
                    disabled={loading}
                />
                <SegmentedControl data={[{label: "Grid", value: "grid"}, {label: "List", value: "list"}]}
                                  value={view} onChange={setView}/>
            </Flex>)}
            {filteredimages.length < 1 && !loading && (
                <EmptyState
                    withIndicatorBackground
                    icon={<IconPackage color={"#2560FF"}/>}
                    title="No images found"
                >
                    <EmptyState.Description>
                        There are no docker images available right now.

                    </EmptyState.Description>
                    <EmptyState.Actions>
                        {/*<Button variant="default">Refresh</Button>*/}
                    </EmptyState.Actions>
                </EmptyState>
            )}


            {view === "grid" && (
                <SimpleGrid
                    cols={{base: 2, sm: cols,}}
                    spacing="sm"
                    style={{transition: "opacity 150ms ease"}}
                >
                    {loading
                        ? Array.from({length: cols}).map((_, i) => <SkeletonCard key={i}/>)
                        : filteredimages.map((image, i) => (
                            <ImageCard image={image} key={i}/>
                        ))}
                </SimpleGrid>
            )}
            {view === "list" && (
                <Stack>
                    {loading
                        ? Array.from({length: 6}).map((_, i) => <SkeletonCard key={i}/>)
                        : filteredimages.map((image, i) => (
                            <ImageCard image={image} key={i}/>
                        ))}
                </Stack>
            )}

            {/*</Container>*/}
        </Stack>
    )
}