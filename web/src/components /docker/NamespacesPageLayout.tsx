import {Link} from '@tanstack/react-router'
import {Hero} from "#/components /core/Hero.tsx";
import {Breadcrumbs, Container, Stack} from "@mantine/core";
import {IconHomeFilled} from "@tabler/icons-react";
import {NamespacesView} from "#/components /docker/NamespacesView.tsx";

export function NamespacesPageLayout({page}: { page?: number }) {
    const breadcrumbItems = [
        {title: <IconHomeFilled size={18}/>, href: '/'},
        {title: 'Namespaces', href: '/namespaces/'},
    ].map((item, index) => (
        <Link to={item.href} key={index}>
            {item.title}
        </Link>
    ));

    return (
        <>
            <Hero/>
            <div>
                <Container pt={40} pb={40}>
                    <Stack>
                        <Breadcrumbs>{breadcrumbItems}</Breadcrumbs>
                        <NamespacesView viewType={"grid"} initialPageSize={24} page={page}/>
                    </Stack>
                </Container>
            </div>
        </>
    )
}
