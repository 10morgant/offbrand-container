import {useState} from 'react';
import {useQuery} from '@tanstack/react-query';
import {Badge, Group, Stack, Text} from '@mantine/core';
import {useDebouncedValue} from '@mantine/hooks';
import {IconBrandDocker, IconFolder} from '@tabler/icons-react';
import {useNavigate} from '@tanstack/react-router';
import {SearchCombobox, type SearchGroup} from '../../core/SearchCombobox';
import {useRegistryContext} from "#/context/RegistryContext.tsx";
import {fetchSearchOptions} from "#/logic/queries.ts";


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

export function SearchServer() {
    const [search, setSearch] = useState('');
    const [debouncedSearch] = useDebouncedValue(search, 300);
    const navigate = useNavigate();
    const {config} = useRegistryContext();
    const trimmed = search.trim();
    const debouncedTrimmed = debouncedSearch.trim();

    const searchQuery = useQuery({
        ...fetchSearchOptions(config?.url ?? "http://example.com", debouncedTrimmed),
        enabled: Boolean(config && debouncedTrimmed.length > 0),
    })

    const packages: PackageInfo[] = (searchQuery.data?.images ?? []).map((image) => {
        const version = image.latest ?? "-"
        const desc = image.tags?.length
            ? `${image.tags?.length} tag${image.tags?.length === 1 ? '' : 's'}: ${image.tags?.slice(0, 5).join(', ')}${image.tags.length > 5 ? '…' : ''}`
            : '';
        const name = image.name
        const namespace = image.namespace_name
        return {name, namespace, version, desc};
    });

    const both: PackageInfo[] = (searchQuery.data?.qualified ?? []).map((image) => {
        const version = image.latest ?? "-"
        const desc = image.tags?.length
            ? `${image.tags?.length} tag${image.tags?.length === 1 ? '' : 's'}: ${image.tags?.slice(0, 5).join(', ')}${image.tags.length > 5 ? '…' : ''}`
            : '';
        const name = image.name
        const namespace = image.namespace_name
        return {name, namespace, version, desc};
    });


    const namespaces: NamespaceInfo[] = (searchQuery.data?.namespaces ?? []).map((ns) => (
        {name: ns.name, imageCount: ns.num_images}
    ));

    const isNamespaceQuery = trimmed.endsWith('/');
    const nsPrefix = isNamespaceQuery ? trimmed.slice(0, -1) : null;
    const isLoading = search !== debouncedSearch || searchQuery.isFetching;
    const isError = searchQuery.isError;


    // This is the only place that knows Docker has two kinds of results.
    // A packages-only use case would just emit a single group here.
    const groups: SearchGroup[] = [
        {
            label: 'Namespaces',
            options: namespaces.map((ns, i) => ({
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
            label: isNamespaceQuery ? `${nsPrefix}/* images` : `Images ${packages.length}`,
            options: packages.map((pkg, i) => ({
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
        {
            label: "Exact matches",
            options: both.map((pkg, i) => ({
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
            emptyMessage={trimmed ? "No matching images" : "Type to search"}
            placeholder={config ? 'Search images or type namespace/…' : 'Configure registry to search…'}
            disabled={!config}
        />
    );
}