import {Text} from "@mantine/core";
import {Link} from "@tanstack/react-router";
import {type JSX} from "react";

export interface BreadcrumItemProps {
    item: {
        title: JSX.Element | string;
        href: string;
    };
    params?: Record<string, string | number | boolean | undefined>;
}

export function BreadcrumItem({item, params}: BreadcrumItemProps) {
    return (
        <Link to={item.href} params={params}>
            <Text style={{textDecoration: 'inherit'}} c={"white"}>
                {item.title}
            </Text>
        </Link>
    );
}