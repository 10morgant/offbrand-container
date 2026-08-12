import {createFileRoute} from '@tanstack/react-router'
import {NamespacesPageLayout} from "#/components /docker/NamespacesPageLayout.tsx";

export const Route = createFileRoute('/namespaces/$page')({
    component: RouteComponent,
})

function RouteComponent() {
    const {page} = Route.useParams();
    const pageNumber = Number.parseInt(page, 10);
    const safePage = Number.isFinite(pageNumber) && pageNumber > 0 ? pageNumber : 1;

    return <NamespacesPageLayout page={safePage} />
}
