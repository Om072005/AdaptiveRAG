/// <reference types="vite/client" />

interface ImportMetaEnv {
  readonly VITE_LIVE_API_URL?: string
  readonly VITE_ALLOW_SAMPLE?: string
  readonly VITE_FORCE_SAMPLE?: string
}

interface ImportMeta {
  readonly env: ImportMetaEnv
}
