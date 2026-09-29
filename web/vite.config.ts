import { readdirSync, rmSync, statSync } from 'node:fs'
import { join } from 'node:path'
import tailwindcss from '@tailwindcss/vite'
import react from '@vitejs/plugin-react'
import { defineConfig, loadEnv, type Plugin } from 'vite'

// Sample data is for local and preview builds only; a production build ships none of it.
function stripSamples(allow: boolean): Plugin {
  const remove = (dir: string) => {
    for (const name of readdirSync(dir)) {
      const path = join(dir, name)
      if (statSync(path).isDirectory()) remove(path)
      else if (name.endsWith('.sample.json')) rmSync(path)
    }
  }
  return {
    name: 'strip-samples',
    apply: 'build',
    closeBundle() {
      if (!allow) remove('dist')
    },
  }
}

export default defineConfig(({ mode }) => {
  const env = loadEnv(mode, process.cwd(), 'VITE_')
  const allowSample = (process.env.VITE_ALLOW_SAMPLE ?? env.VITE_ALLOW_SAMPLE) === '1'
  return { plugins: [react(), tailwindcss(), stripSamples(allowSample)] }
})
