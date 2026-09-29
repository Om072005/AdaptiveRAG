import { defineConfig } from '@playwright/test'

// Runs against a sample build served locally; the installed Edge avoids a browser download.
export default defineConfig({
  testDir: 'tests',
  use: { baseURL: 'http://localhost:4174', channel: 'msedge' },
  webServer: {
    command: 'npx vite build && npx vite preview --port 4174 --strictPort',
    env: { VITE_ALLOW_SAMPLE: '1' },
    url: 'http://localhost:4174',
    reuseExistingServer: false,
  },
})
