import { readdir, readFile, writeFile } from "node:fs/promises";
import path from "node:path";
import { fileURLToPath } from "node:url";

const scriptDirectory = path.dirname(fileURLToPath(import.meta.url));
const outputDirectory = path.resolve(scriptDirectory, "..", "out");

async function htmlFiles(directory) {
  const entries = await readdir(directory, { withFileTypes: true });
  const nested = await Promise.all(
    entries.map(async (entry) => {
      const target = path.join(directory, entry.name);
      if (entry.isDirectory()) return htmlFiles(target);
      return entry.isFile() && entry.name.endsWith(".html") ? [target] : [];
    }),
  );
  return nested.flat();
}

function stripFrameworkRuntime(html) {
  return html
    .replace(
      /<link\b(?=[^>]*\brel=["']preload["'])(?=[^>]*\bas=["']script["'])[^>]*>\s*/gi,
      "",
    )
    .replace(
      /<script\b[^>]*\bsrc=["'][^"']*\/_next\/static\/chunks\/[^"']+["'][^>]*>\s*<\/script>\s*/gi,
      "",
    )
    .replace(
      /<script>(?=[\s\S]*?self\.__next_f)[\s\S]*?<\/script>\s*/gi,
      "",
    );
}

const files = await htmlFiles(outputDirectory);
for (const file of files) {
  const source = await readFile(file, "utf8");
  const output = stripFrameworkRuntime(source);
  await writeFile(file, output, "utf8");
}

const indexPath = path.join(outputDirectory, "index.html");
const index = await readFile(indexPath, "utf8");
if (index.includes("self.__next_f") || /<script[^>]+\/_next\/static\/chunks\//i.test(index)) {
  throw new Error("Static export still contains a Next.js hydration runtime.");
}
if (!index.includes('data-static-behavior="chapter-navigation"')) {
  throw new Error("Static chapter navigation behavior was removed unexpectedly.");
}

console.log(`Removed unused hydration runtime from ${files.length} static HTML files.`);
