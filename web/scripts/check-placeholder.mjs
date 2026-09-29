// The design rules that already apply to the placeholder (02_DESIGN_SYSTEM.md section 10).
import { readFileSync } from 'node:fs';

const html = readFileSync('index.html', 'utf8');
const banned = [/gradient/i, /box-shadow/i, /drop-shadow/i, /backdrop-filter/i, /blur\(/i, /uppercase/i, /\u2192|\u2014|\u2013/];
const hits = banned.filter((re) => re.test(html));
if (!html.includes('<div id="root"')) hits.push('missing <div id="root">');
if (hits.length) {
  console.error('design check failed on web/index.html:', hits.map(String).join(', '));
  process.exit(1);
}
