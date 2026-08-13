import {createFileRoute, Link} from '@tanstack/react-router'
import {colourTheme} from "#/config/colours.ts";
import {Breadcrumbs, Button, Container, Flex, Stack, Text, Title} from "@mantine/core";
import {IconArrowLeft, IconHomeFilled} from "@tabler/icons-react";
import {useQuery} from "@tanstack/react-query";
import {fetchNamespaceOptions} from "#/logic/queries.ts";
import {useRegistryContext} from "#/context/RegistryContext.tsx";
import {ImagesView} from "#/components /docker/ImagesView.tsx";
import {BreadcrumItem} from "#/components /core/BreadcrumItem.tsx";

export const Route = createFileRoute('/$namespace/')({
    component: RouteComponent,
})


function RouteComponent() {
    const {namespace} = Route.useParams()
    const {config} = useRegistryContext()
    const {data, isLoading} = useQuery(fetchNamespaceOptions(config?.url ?? "http://example.com", namespace))

    const breadcrumbItems = [
        {title: <IconHomeFilled size={18}/>, href: '/'},
        {title: namespace, href: ''},
    ].map((item, index) => (
        <BreadcrumItem key={index} item={item} params={{namespace: namespace}}/>
    ));

    return (
        <>
            <div style={{backgroundColor: colourTheme.hero_body}}>
                <Container size={1200} pt={40} pb={40}>
                    <Stack gap={60}>
                        <Stack>
                            <Breadcrumbs>{breadcrumbItems}</Breadcrumbs>
                            <Flex>
                                <Button
                                    radius={3}
                                    leftSection={<IconArrowLeft size={16}/>}
                                    component={Link}
                                    to={"/"}
                                >
                                    Back to search
                                </Button>
                            </Flex>
                            <Flex justify={"space-between"}>
                                <Stack gap={0}>
                                    <Text fz={"14x"} fw={500} tt="uppercase">
                                        namespace
                                    </Text>
                                    <Title order={1} fw={500} fz={"36px"}
                                           ff={'ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, "Liberation Mono", "Courier New", monospace'}>
                                        {namespace}/
                                    </Title>
                                </Stack>

                            </Flex>
                        </Stack>
                    </Stack>
                </Container>
            </div>
            <Container size={1200} pt={40} pb={40}>
                <ImagesView viewType={"grid"} data={data} loading={isLoading}/>

            </Container>
        </>
    )
}
