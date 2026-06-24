import { cp, rm } from 'node:fs/promises';
import { join, dirname } from 'node:path';
import { fileURLToPath } from 'node:url';

const __dirname = dirname(fileURLToPath(import.meta.url));
const src = join(__dirname, '..', 'dist');
const dest = join(__dirname, '..', '..', 'web_app', 'static');

// 需要保留的目录/文件（不会被删除）
const KEEP = new Set(['files']);

async function main() {
  // 1. 清理 static 目录中上次构建的前端文件（保留 files 等用户数据）
  const existing = await readDirSafe(dest);
  for (const name of existing) {
    if (!KEEP.has(name)) {
      console.log(`  [clean] Removing ${name}`);
      await rm(join(dest, name), { recursive: true, force: true });
    }
  }

  // 2. 复制 dist 产物到 static
  console.log(`  [copy] dist/ -> ${dest}`);
  await cp(src, dest, { recursive: true });

  console.log(`  ✓ Build artifacts copied to ${dest}`);
}

async function readDirSafe(dir) {
  try {
    const entries = await import('node:fs/promises').then(fs => fs.readdir(dir));
    return entries;
  } catch {
    return [];
  }
}

main().catch(err => {
  console.error('Copy build failed:', err);
  process.exit(1);
});
