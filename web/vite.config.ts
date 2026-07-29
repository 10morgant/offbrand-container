import {defineConfig} from 'vite'

import {tanstackRouter} from '@tanstack/router-plugin/vite'

import viteReact from '@vitejs/plugin-react'

const config = defineConfig({
    resolve: {tsconfigPaths: true},
    // base: "/ui/",
    plugins: [
        tanstackRouter({target: 'react', autoCodeSplitting: true}),
        viteReact(),
    ],
    server: {
        proxy: {
            '/api': {
                target: 'http://localhost:8000',
                changeOrigin: true,
                // uncomment if your backend doesn't expect the /api prefix:
                // rewrite: (path) => path.replace(/^\/api/, ''),
            },
        },
    },
})

export default config
