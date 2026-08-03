import {createFileRoute, Link} from '@tanstack/react-router'
import {Hero} from "#/components /core/Hero.tsx";
import {Breadcrumbs, Container, Stack} from "@mantine/core";
import {IconHomeFilled} from "@tabler/icons-react";
import {NamespacesView} from "#/components /docker/NamespacesView.tsx";

export const Route = createFileRoute('/namespaces/')({
    component: RouteComponent,
})

function RouteComponent() {
    const breadcrumbItems = [
        {title: <IconHomeFilled size={18}/>, href: '/'},
        {title: 'Namespaces', href: ''},
    ].map((item, index) => (
        <Link to={item.href} key={index}>
            {item.title}
        </Link>
    ));

    return (
        <>
            <Hero/>
            <div
                // style={{backgroundColor: colourTheme.surface_2}}
            >
                <Container size={1200} pt={40} pb={40}>
                    <Stack>
                        <Breadcrumbs>{breadcrumbItems}</Breadcrumbs>
                        <NamespacesView viewType={"grid"} pageSize={100}/>
                    </Stack>
                </Container>
            </div>
        </>
    )
}
