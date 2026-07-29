import {createFileRoute} from '@tanstack/react-router'
import {NamespacesView} from "#/components /docker/NamespacesView.tsx";
import {Container, NumberFormatter, SimpleGrid} from "@mantine/core";
import {Hero} from "#/components /core/Hero.tsx";
import {IconBox, IconFolder, IconServer, IconTag} from "@tabler/icons-react";
import {StatCard} from "#/components /core/StatsCards.tsx";
import {useRegistryContext} from "#/context/RegistryContext.tsx";
import {colourTheme} from "#/config/colours.ts";
import {useQuery} from "@tanstack/react-query";
import {fetchImagesOptions, fetchStatsOptions} from "#/logic/queries.ts";
import {ImagesView} from "#/components /docker/ImagesView.tsx";

export const Route = createFileRoute('/')({component: Home})

function Home() {
    const {config} = useRegistryContext()

    const {data} = useQuery(fetchStatsOptions(config?.url ?? "http://example.com"))
    const {data: ims, isLoading} = useQuery(fetchImagesOptions(config?.url ?? "http://example.com", 24, 0))

    const images = ims?.items ?? []

    return (
        <>
            <Hero/>
            <div style={{backgroundColor: colourTheme.brand_dark}}>
                <Container size={1600} pt={40} pb={40}>
                    <SimpleGrid cols={4}>
                        <StatCard
                            icon={<IconFolder size={24}/>}
                            label="Total Namespaces"
                            value={<NumberFormatter value={data?.namespaces} thousandSeparator />}
                            loading={false}
                            color="yellow"
                        />
                        <StatCard
                            icon={<IconBox size={24}/>}
                            label="Total Images"
                            value={<NumberFormatter value={data?.images} thousandSeparator />}
                            loading={false}
                            color="blue"
                        />
                        <StatCard
                            icon={<IconTag size={24}/>}
                            label="Total Tags"
                            value={<NumberFormatter value={data?.tags} thousandSeparator />}
                            loading={false}
                            color="violet"
                        />
                        <StatCard
                            icon={<IconServer size={24}/>}
                            label="Current Registry"
                            // value={config?.url ? (new URL(config?.url).toString()) : ""}
                            value={config?.name}
                            loading={false}
                            color="teal"
                        />
                    </SimpleGrid>
                </Container>
            </div>

            <div>
                <Container size={1600} pt={40} pb={40}>
                    <NamespacesView/>
                </Container>
            </div>
            <div>
                <Container size={1600} pt={40} pb={40}>
                    <ImagesView
                        viewType={"grid"}
                        showSearch={false}
                        images={images}
                        cols={4}
                        total={ims?.total}
                        loading={isLoading}
                    />

                </Container>
            </div>
        </>
    )
}
