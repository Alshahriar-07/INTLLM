/**
 * Copy the canonical installer scripts from IRM_INSTALL/ into public/ so the
 * Vercel deployment serves them verbatim at:
 *
 *   https://intllm.vercel.app/install.ps1
 *   https://intllm.vercel.app/install.sh
 *
 * Runs automatically before `npm run build` (prebuild). IRM_INSTALL/ stays the
 * single source of truth; public/ holds generated copies.
 */
import { copyFileSync, existsSync, mkdirSync, readFileSync, writeFileSync } from 'node:fs';
import { dirname, resolve } from 'node:path';
import { fileURLToPath } from 'node:url';

const root = resolve(dirname(fileURLToPath(import.meta.url)), '..');

const PAIRS = [
  ['IRM_INSTALL/install.ps1', 'public/install.ps1'],
  ['IRM_INSTALL/install.sh', 'public/install.sh']
];

mkdirSync(resolve(root, 'public'), { recursive: true });

for (const [source, destination] of PAIRS) {
  const src = resolve(root, source);
  const dest = resolve(root, destination);
  if (!existsSync(src)) {
    console.error(`[sync-installers] missing source: ${source}`);
    process.exit(1);
  }
  copyFileSync(src, dest);
  console.log(`[sync-installers] ${source} -> ${destination}`);
}

// Sanity-check that the shell script keeps a real shebang; a bad copy would
// make `curl ... | bash` fail confusingly.
const sh = readFileSync(resolve(root, 'public/install.sh'), 'utf8');
if (!sh.startsWith('#!/usr/bin/env bash')) {
  console.error('[sync-installers] public/install.sh is missing its shebang');
  process.exit(1);
}

// Ensure both copies are byte-identical (guards against manual drift).
for (const [source, destination] of PAIRS) {
  const a = readFileSync(resolve(root, source), 'utf8');
  const b = readFileSync(resolve(root, destination), 'utf8');
  if (a !== b) {
    console.error(`[sync-installers] ${destination} is out of sync with ${source}`);
    process.exit(1);
  }
}

writeFileSync(resolve(root, 'public/.nojekyll'), '');
