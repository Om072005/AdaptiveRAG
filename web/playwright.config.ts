import { defineConfig } from '@playwright/test'

// Sample builds served locally; the installed Edge avoids a browser download. The live project is
// the local dev setup (VITE_LIVE_API_URL set, API answers mocked in the test); the other is replay only.
export default defineConfig({
  testDir: 'tests',
  use: { channel: 'msedge' },
  projects: [
    { name: 'replay', testIgnore: /live\.spec/, use: { baseURL: 'http://localhost:4174' } },
    { name: 'live', testMatch: /live\.spec/, use: { baseURL: 'http://localhost:4175' } },
  ],
  webServer: [
    {
      command: 'npx vite build --outDir node_modules/.smoke/replay && npx vite preview --outDir node_modules/.smoke/replay --port 4174 --strictPort',
      env: { VITE_ALLOW_SAMPLE: '1', VITE_LIVE_API_URL: '' },
      url: 'http://localhost:4174',
    },
    {
      command: 'npx vite build --outDir node_modules/.smoke/live && npx vite preview --outDir node_modules/.smoke/live --port 4175 --strictPort',
      env: { VITE_ALLOW_SAMPLE: '1', VITE_LIVE_API_URL: 'http://localhost:4175' },
      url: 'http://localhost:4175',
    },
  ],
})
