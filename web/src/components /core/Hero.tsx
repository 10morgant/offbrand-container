import {Container, Stack, Title} from "@mantine/core";
import {colourTheme} from "#/config/colours.ts";
import {SearchBar} from "#/components /docker/Search.ts";

export function Hero() {
    return (
        <div style={{backgroundColor: colourTheme.hero_body}}>
            <Container size={1600} pt={40} pb={40}>
                <Stack align="center" justify="center" gap={60}>
                    <Stack align="center" justify="center">
                        <Title order={6} tt="uppercase">
                            Internal Package Registry
                        </Title>
                        <Title order={1}>
                            Search the{' '}
                            <span
                                style={{
                                    backgroundColor: colourTheme.brand,
                                    padding: 10,
                                }}
                            >
                                docker mirror
                            </span>
                        </Title>

                    </Stack>
                    <SearchBar/>
                </Stack>
            </Container>
        </div>
    );
}