import {useMemo, useState} from 'react';
import {useQuery} from '@tanstack/react-query';
import {compareItems, rankings, rankItem} from '@tanstack/match-sorter-utils';
import {Badge, Group, Stack, Text} from '@mantine/core';
import {IconBrandDocker, IconFolder} from '@tabler/icons-react';
import {useNavigate} from '@tanstack/react-router';
import {SearchCombobox, type SearchGroup} from '../../core/SearchCombobox';
import {useRegistryContext} from "#/context/RegistryContext.tsx";
import {fetchImagesOptions, fetchNamespacesOptions} from "#/logic/queries.ts";


type PackageInfo = {
    name: string;
    namespace: string;
    version: string;
    desc: string;
};

type NamespaceInfo = {
    name: string;
    imageCount: number;
};

// Sentinel prefix to distinguish namespace options in handleSubmit
const NS_PREFIX = '__ns__:';

export function SearchClient() {
    const [search, setSearch] = useState('');
    const navigate = useNavigate();
    const {config} = useRegistryContext();

    const namespaceQuery = useQuery(fetchNamespacesOptions(config?.url ?? "http://example.com", 0, 0))
    const imageQuery = useQuery(fetchImagesOptions(config?.url ?? "http://example.com", 0, 0))

    const packages: PackageInfo[] = (imageQuery.data?.items ?? []).map((image) => {
        const version = image.latest
        const desc = image.tags.length
            ? `${image.tags.length} tag${image.tags.length === 1 ? '' : 's'}: ${image.tags.slice(0, 5).join(', ')}${image.tags.length > 5 ? '…' : ''}`
            : '';
        const name = image.name
        const namespace = image.namespace_name
        return {name, namespace, version, desc};
    });

    const namespaces: NamespaceInfo[] = (namespaceQuery.data?.items ?? []).map((ns) => (
        {name: ns.name, imageCount: ns.num_images}
    ));

    const trimmed = search.trim();
    const isNamespaceQuery = trimmed.endsWith('/');
    const nsPrefix = isNamespaceQuery ? trimmed.slice(0, -1) : null;

    // Namespace suggestions shown when query matches a namespace name (with or without trailing /)

    const filteredPackages = useMemo(() => {
        if (!trimmed) return packages.slice(0, 20);

        const scored = packages
            .map((pkg) => ({pkg, itemRank: rankItem(pkg.name, trimmed)}))
            .filter((x) => x.itemRank.passed);
        scored.sort((a, b) => compareItems(a.itemRank, b.itemRank));
        return scored.map((x) => x.pkg);
    }, [packages, trimmed]);


    const filteredNamespaces = useMemo(() => {
        if (!trimmed) return namespaces.slice(0, 20);
        const scored = namespaces
            .map((pkg) => ({pkg, itemRank: rankItem(pkg.name, trimmed, {threshold: rankings.WORD_STARTS_WITH})}))
            .filter((x) => x.itemRank.passed);
        scored.sort((a, b) => compareItems(a.itemRank, b.itemRank));
        console.table(scored)
        return scored.map((x) => x.pkg);
    }, [namespaces, trimmed]);

    const isLoading = imageQuery.isLoading || namespaceQuery.isLoading;
    const isError = imageQuery.isError || namespaceQuery.isError;


    // This is the only place that knows Docker has two kinds of results.
    // A packages-only use case would just emit a single group here.
    const groups: SearchGroup[] = [
        {
            label: 'Namespaces',
            options: filteredNamespaces.map((ns, i) => ({
                value: `${NS_PREFIX}${ns.name}`,
                content: (
                    <Group gap={8} key={`ns_${i}`}>
                        <IconFolder color="var(--mantine-color-yellow-4)"/>
                        {/*<IconChartCohort color="var(--mantine-color-yellow-4)"/>*/}
                        <Text fw={600} c="#e8edf1">{ns.name}/</Text>
                        <Badge size="xs" variant="light" color="yellow">{ns.imageCount} images</Badge>
                    </Group>
                ),
            })),
        },
        {
            label: isNamespaceQuery ? `${nsPrefix}/* images` : `Images ${filteredPackages.length}`,
            options: filteredPackages.map((pkg, i) => ({
                value: `${pkg.namespace}/${pkg.name}`,
                content: (
                    <Stack key={`im_${i}`} gap={3}>
                        <Group gap={6}>
                            <IconBrandDocker color={"#2560FF"}/>
                            {/*<Highlight highlight={trimmed} size="sm" c="#2496ED">*/}
                            <Text fw={600} c="#e8edf1">{pkg.namespace}/{pkg.name}</Text>
                            {/*</Highlight>*/}
                            {/*<Text size="sm" c="#2496ED">{pkg.version}</Text>*/}
                        </Group>
                        <Text size="sm" c="#5a6672">{pkg.desc}</Text>
                    </Stack>
                ),
            })),
        },
    ];

    const handleSubmit = (value: string) => {
        if (value.startsWith(NS_PREFIX)) {
            const ns = value.slice(NS_PREFIX.length);
            setSearch('');
            navigate({to: '/$namespace', params: {namespace: ns}});
        } else {
            const [ns, im] = value.split("/")
            setSearch(value);
            navigate({to: '/$namespace/$image', params: {namespace: ns, image: im}});
        }
    };

    return (
        <SearchCombobox
            search={search}
            onSearchChange={setSearch}
            onSubmit={handleSubmit}
            groups={groups}
            allowFreeTextSubmit={!isNamespaceQuery}
            isLoading={isLoading}
            isError={isError}
            errorMessage="Couldn't reach registry"
            emptyMessage="No matching images"
            placeholder={config ? 'Search images or type namespace/…' : 'Configure registry to search…'}
            disabled={!config}
        />
    );
}