import { type ReactNode } from 'react';
import { Combobox, useCombobox, TextInput, Button, Text, Loader } from '@mantine/core';
import { IconSearch } from '@tabler/icons-react';
import {colourTheme} from "#/config/colours.ts";

export type SearchOption = {
    /** Value passed to onSubmit / onOptionSubmit when this option is picked */
    value: string;
    /** Fully custom rendered content for the option row */
    content: ReactNode;
};

export type SearchGroup = {
    label: string;
    options: SearchOption[];
};

export type SearchComboboxProps = {
    /** Controlled search text */
    search: string;
    onSearchChange: (value: string) => void;
    /** Called when the user picks an option, or submits free text via Enter/Go */
    onSubmit: (value: string) => void;
    /** Already-filtered, grouped options to render. Groups with 0 options are hidden. */
    groups: SearchGroup[];
    /**
     * Whether Enter / the Go button should submit the raw search text.
     * Set to false while the current text represents an intermediate/incomplete
     * query (e.g. a namespace prefix that isn't a submittable value on its own).
     */
    allowFreeTextSubmit?: boolean;
    isLoading?: boolean;
    isError?: boolean;
    errorMessage?: string;
    emptyMessage?: string;
    placeholder?: string;
    disabled?: boolean;
    width?: number | string;
    goButtonLabel?: string;
};

export function SearchCombobox({
                                   search,
                                   onSearchChange,
                                   onSubmit,
                                   groups,
                                   allowFreeTextSubmit = true,
                                   isLoading = false,
                                   isError = false,
                                   errorMessage = "Couldn't load results",
                                   emptyMessage = 'No matches',
                                   placeholder = 'Search…',
                                   disabled = false,
                                   width = 900,
                                   goButtonLabel = '→ Go',
                               }: SearchComboboxProps) {
    const combobox = useCombobox();
    const trimmed = search.trim();
    const hasAnyOptions = groups.some((g) => g.options.length > 0);

    const handleSubmit = (value: string) => {
        combobox.closeDropdown();
        onSubmit(value);
    };

    return (
        <div style={{ width}}>
            <Combobox
                store={combobox}
                onOptionSubmit={handleSubmit}
                styles={{
                    dropdown: { backgroundColor: '#17191e', border: '1px solid #24303a', padding: 0, marginTop:-10 },
                }} radius={0}

            >
                <Combobox.Target>
                    <TextInput
                        value={search}
                        onChange={(e) => {
                            onSearchChange(e.currentTarget.value);
                            combobox.openDropdown();
                            combobox.resetSelectedOption();
                        }}
                        onFocus={() => combobox.openDropdown()}
                        onClick={() => combobox.openDropdown()}
                        onKeyDown={(e) => {
                            if (e.key === 'Enter' && trimmed && allowFreeTextSubmit) handleSubmit(trimmed);
                        }}
                        placeholder={placeholder}
                        disabled={disabled}
                        leftSection={isLoading ? <Loader size={14} color="#2496ED" /> : <IconSearch size={16} color={colourTheme.brand} />}
                        rightSectionWidth={90}
                        radius={0}
                        rightSection={
                            <Button
                                size="sm"
                                radius={0}
                                styles={{ root: { height: '100%', width: '100%', backgroundColor:colourTheme.brand } }}
                                onClick={() => trimmed && allowFreeTextSubmit && handleSubmit(trimmed)}
                            >
                                {goButtonLabel}
                            </Button>
                        }
                        styles={{
                            input: { backgroundColor: '#0d0f12', border: '1px solid #24303a', color: '#e8edf1', height: 52 },
                        }}
                    />
                </Combobox.Target>

                <Combobox.Dropdown>
                    <Combobox.Options mah={360} style={{ overflowY: 'auto' }}>
                        {isError && (
                            <Combobox.Empty>
                                <Text size="sm" c="red">{errorMessage}</Text>
                            </Combobox.Empty>
                        )}

                        {!isError && !hasAnyOptions && (
                            <Combobox.Empty>
                                <Text size="sm" c="#5a6672">{emptyMessage}</Text>
                            </Combobox.Empty>
                        )}

                        {!isError &&
                            groups.map(
                                (group) =>
                                    group.options.length > 0 && (
                                        <Combobox.Group label={group.label} key={group.label}>
                                            {group.options.map((opt) => (
                                                <Combobox.Option
                                                    value={opt.value}
                                                    key={opt.value}
                                                    style={{ padding: '12px 16px', borderBottom: '1px solid #1c232b' }}
                                                >
                                                    {opt.content}
                                                </Combobox.Option>
                                            ))}
                                        </Combobox.Group>
                                    )
                            )}
                    </Combobox.Options>
                </Combobox.Dropdown>
            </Combobox>
        </div>
    );
}