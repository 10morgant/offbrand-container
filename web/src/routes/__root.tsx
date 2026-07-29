import {createRootRoute, Link, Outlet} from '@tanstack/react-router'
import {
    AppShell,
    AppShellHeader,
    createTheme,
    Group,
    MantineProvider,
    Select,
    Text,
    ThemeIcon,
    Title,
} from '@mantine/core'
import {QueryClient, QueryClientProvider, useQuery} from '@tanstack/react-query'

import '../styles.css'
import '@mantine/core/styles.css'
import {RegistryProvider, useRegistryContext} from "#/context/RegistryContext.tsx";
import {colourTheme} from "#/config/colours.ts";
import {IconBrandDocker} from "@tabler/icons-react";
import {fetchLastUpdatedOptions, fetchRegistriesOptions} from "#/logic/queries.ts";
import {formatDate} from "#/logic/utils.ts";
import type {Registry} from "#/logic/types.ts";
import {Apps} from "#/components /core/Apps.tsx";

const queryClient = new QueryClient()

export const Route = createRootRoute({
    component: RootComponent,
})

const theme = createTheme({
    colors: {
        theme: [
            "#e6f0ff",
            "#cddcff",
            "#9ab6ff",
            "#638eff",
            "#366cff",
            "#2560ff",
            "#014cff",
            "#003de5",
            "#0036ce",
            "#00153C"
        ]
    },
    components: {
        AppShellHeader: AppShellHeader.extend({
            defaultProps: {
                bg: colourTheme.hero_top
            }
        })
    },
    fontFamily: "ui-sans-serif, system-ui, sans-serif, 'Apple Color Emoji', 'Segoe UI Emoji', 'Segoe UI Symbol', 'Noto Color Emoji'"
})

function AppHeader() {
    const {config, setConfig} = useRegistryContext()
    const {data: registries} = useQuery(fetchRegistriesOptions())
    const {data: last_updated} = useQuery(fetchLastUpdatedOptions())

    if (!config?.url && registries) {
        const reg: Registry = registries[0]
        setConfig({url: reg.url, name: reg.display_name?? reg.url})
    }

    return (
        <>
            <AppShell.Header p="15">
                <Group justify="space-between" h="100%">
                    <Group>
                        <Apps/>
                        <Link to="/" style={{
                            textDecoration: 'none',
                            color: 'inherit',
                            display: 'flex',
                            alignItems: 'center',
                            gap: 12
                        }}>
                            <ThemeIcon size="40" variant="light">
                                <IconBrandDocker/>
                            </ThemeIcon>
                            <Title order={4}>Docker Registry UI</Title>
                        </Link>
                    </Group>
                    <Group>
                        <Text> Last updated: {formatDate(last_updated?.timestamp ?? "-")} </Text>
                        <Text>Registry: </Text>
                        <Select
                            data={registries?.map((reg) => (
                                {label: reg.display_name, value: reg.url}
                            )) ?? []}
                            value={config?.url ?? "??"}
                            onChange={(val, option) => {
                                if (val) {
                                    setConfig({url: val, name: option.label})
                                }
                            }}
                        />
                    </Group>

                </Group>
            </AppShell.Header>
        </>
    )
}

function RootComponent() {
    return (
        <MantineProvider theme={theme} forceColorScheme="dark">
            <QueryClientProvider client={queryClient}>
                <RegistryProvider>
                    <AppShell header={{height: 70}}>
                        <AppHeader/>
                        <AppShell.Main style={{backgroundColor: colourTheme.page}}>
                            <Outlet/>
                        </AppShell.Main>
                    </AppShell>
                </RegistryProvider>
            </QueryClientProvider>
        </MantineProvider>
    )
}
