import { defineConfig } from 'tsup'

export default defineConfig({
  entry: ['app/**/*.ts'],
  format: ['esm'],
  target: 'es2020',
  outDir: 'dist',
  clean: true,
  dts: true,
  treeshake: true,
  splitting: true,
  external: ['@vercel/workflow']
})