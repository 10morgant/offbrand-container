import {createContext, type ReactNode, useContext, useState} from 'react'

export type RegistryConfig = {
    url: string
    name: string
}

let registryConfig: RegistryConfig | null = null

export const setRegistryConfig = (config: RegistryConfig) => {
    registryConfig = config
    localStorage.setItem('registryConfig', JSON.stringify(config))
}

export const getRegistryConfig = (): RegistryConfig | null => {
    if (registryConfig) return registryConfig

    const stored = localStorage.getItem('registryConfig')
    if (stored) {
        try {
            registryConfig = JSON.parse(stored)
            return registryConfig
        } catch {
            return null
        }
    }
    return null
}

interface RegistryContextValue {
    config: RegistryConfig | null
    setConfig: (config: RegistryConfig) => void
}

const RegistryContext = createContext<RegistryContextValue | null>(null)

export function RegistryProvider({children}: { children: ReactNode }) {
    const [config, setConfigState] = useState<RegistryConfig | null>(() => getRegistryConfig())

    const setConfig = (newConfig: RegistryConfig) => {
        setRegistryConfig(newConfig)
        setConfigState(newConfig)
    }

    return (
        <RegistryContext.Provider
            value={{
                config,
                setConfig,
            }}
        >
            {children}
        </RegistryContext.Provider>
    )
}

export function useRegistryContext() {
    const ctx = useContext(RegistryContext)
    if (!ctx) throw new Error('useRegistryContext must be used within RegistryProvider')
    return ctx
}

