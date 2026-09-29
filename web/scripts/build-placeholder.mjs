// Placeholder build: copy index.html into dist. Replaced by the Vite build on D6.
import { copyFileSync, mkdirSync } from 'node:fs';

mkdirSync('dist', { recursive: true });
copyFileSync('index.html', 'dist/index.html');
console.log('built dist/index.html');
