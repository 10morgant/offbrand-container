import {Card, Skeleton} from "@mantine/core";

export function SkeletonCard() {
    return (
        <Card p="md" radius="md" withBorder>
            <Skeleton height={20} width="50%" mb={8}/>
            <Skeleton height={14} width="30%"/>
        </Card>
    );
}