import {Group, Paper, Skeleton, Text, ThemeIcon} from '@mantine/core'
import {type JSX} from "react";


interface StatCardProps {
    icon: React.ReactNode
    label: string
    value: string | number | JSX.Element | undefined
    loading: boolean
    color?: string
}

export function StatCard({icon, label, value, loading, color = 'blue'}: StatCardProps) {
    return (
        <Paper p="lg" radius="md" withBorder style={{flex: 1}}>
            <Group>
                <ThemeIcon size={48} radius="md" color={color} variant="light">
                    {icon}
                </ThemeIcon>
                <div>
                    <Text size="xs" c="dimmed" tt="uppercase" fw={600}>
                        {label}
                    </Text>
                    {loading ? (
                        <Skeleton height={28} width={80} mt={4}/>
                    ) : (
                        <Text fw={700} size="xl">
                            {value ?? '—'}
                        </Text>
                    )}
                </div>
            </Group>
        </Paper>
    )
}


