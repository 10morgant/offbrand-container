import {createFileRoute, Link} from '@tanstack/react-router'
import {colourTheme} from "#/config/colours.ts";
import {
    ActionIcon,
    Badge,
    Breadcrumbs,
    Button,
    Code,
    Container,
    CopyButton,
    Flex,
    Group,
    Paper,
    Stack,
    Text,
    Title,
    Tooltip
} from "@mantine/core";
import {IconArrowLeft, IconCheck, IconCopy, IconHomeFilled, IconInfoCircle} from "@tabler/icons-react";
import {TagView} from "#/components /docker/TagsView.tsx";
import {useQuery} from "@tanstack/react-query";
import {fetchNamespaceImageOptions} from "#/logic/queries.ts";
import {useRegistryContext} from "#/context/RegistryContext.tsx";
import {getUrlString} from "#/logic/utils.ts";
import {BreadcrumItem} from "#/components /core/BreadcrumItem.tsx";

export const Route = createFileRoute('/$namespace/$image/')({
    component: RouteComponent,
})


function RouteComponent() {
    const {namespace, image} = Route.useParams()
    const {config} = useRegistryContext()
    const {
        data,
        isLoading
    } = useQuery(fetchNamespaceImageOptions(config?.url ?? "http://example.com", namespace, image))

    const breadcrumbItems = [
        {title: <IconHomeFilled size={18}/>, href: '/'},
        {title: namespace, href: '/$namespace'},
        {title: image, href: ''},
    ].map((item, index) => (
        <BreadcrumItem key={index} item={item} params={{namespace: namespace}}/>
    ));

    return (
        <>
            <div style={{backgroundColor: colourTheme.hero_body}}>
                <Container size={1400} pt={40} pb={40}>
                    <Stack gap={60}>
                        <Stack>
                            <Flex justify={"space-between"}>
                                <Breadcrumbs>{breadcrumbItems}</Breadcrumbs>
                                {data?.self_hosted && <Badge leftSection={<IconInfoCircle/>} radius={"sm"} size={"xl"}
                                                             color={"red"}> SELF-HOSTED package</Badge>}
                            </Flex>
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
                                        Image
                                    </Text>
                                    <Title order={1} fw={500} fz={"36px"}
                                           ff={'ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, "Liberation Mono", "Courier New", monospace'}>
                                        <Link to={"/$namespace"} params={{namespace}} style={{
                                            textDecoration: 'inherit',
                                            color: "white"
                                        }}>{namespace}</Link>/{image}
                                    </Title>
                                </Stack>
                                {/*<Stack gap={0}>
                                    <Flex gap={10} align={"center"}>
                                        <Text fz={"14px"} fw={500} tt="uppercase">
                                            Latest
                                        </Text>
                                        <span style={{color: "rgb(93, 202, 165)"}}>9.4.2</span>
                                    </Flex>
                                    <Flex gap={10} align={"center"}>
                                        <Text fz={"14px"} fw={500} tt="uppercase">
                                            Updated
                                        </Text>
                                        <span style={{color: "#fff"}}>2026-07-21</span>
                                    </Flex>
                                </Stack>*/}
                            </Flex>
                        </Stack>
                    </Stack>
                </Container>
            </div>
            <Container size={1400} pt={40}>
                <Stack>
                    <Paper withBorder p={10}>
                        Docker pull command
                        <Group pt={10} w={"100%"}>
                            <Code p={10} fz={16} w={"95%"}>
                                $ <span
                                style={{color: "rgb(121, 192, 255)"}}>docker</span> pull {getUrlString(config?.url ?? "http://docker.io")}/{namespace}/{image}
                            </Code>
                            <CopyButton
                                value={`docker pull ${getUrlString(config?.url ?? "http://docker.io")}/${namespace}/${image}`}
                                timeout={2000}>
                                {({copied, copy}) => (
                                    <Tooltip
                                        label={copied ? 'Copied!' : 'Copy pull command'}
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
                        </Group>
                    </Paper>
                    <TagView data={data} loading={isLoading}/>
                </Stack>
            </Container>
        </>
    )
}
