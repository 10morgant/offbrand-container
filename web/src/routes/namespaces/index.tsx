import {createFileRoute} from '@tanstack/react-router'
import {NamespacesPageLayout} from "#/components /docker/NamespacesPageLayout.tsx";

export const Route = createFileRoute('/namespaces/')({
    component: RouteComponent,
})

function RouteComponent() {
    return <NamespacesPageLayout />
}
