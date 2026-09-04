import { createReadStream, existsSync, statSync } from "node:fs";
import { createServer } from "node:http";
import { extname, join, normalize, resolve } from "node:path";

const host = process.env.STATIC_HOST ?? "127.0.0.1";
const port = Number.parseInt(process.env.STATIC_PORT ?? "3000", 10);
const root = resolve(process.cwd(), "out");
const configuredBasePath = process.env.NEXT_PUBLIC_BASE_PATH ?? "/payments-analytics";
const basePath =
  configuredBasePath === "/"
    ? ""
    : `/${configuredBasePath.replace(/^\/+|\/+$/g, "")}`;

const contentTypes = {
  ".css": "text/css; charset=utf-8",
  ".html": "text/html; charset=utf-8",
  ".ico": "image/x-icon",
  ".js": "text/javascript; charset=utf-8",
  ".json": "application/json; charset=utf-8",
  ".png": "image/png",
  ".svg": "image/svg+xml",
  ".txt": "text/plain; charset=utf-8",
  ".woff": "font/woff",
  ".woff2": "font/woff2",
  ".xml": "application/xml; charset=utf-8",
};

if (!existsSync(root)) {
  throw new Error("Static export not found. Run npm run build before serve:static.");
}

createServer((request, response) => {
  const requestUrl = new URL(request.url ?? "/", `http://${host}:${port}`);
  let pathname = decodeURIComponent(requestUrl.pathname);

  if (basePath && (pathname === "/" || pathname === basePath)) {
    response.writeHead(308, { Location: `${basePath}/` });
    response.end();
    return;
  }

  if (basePath && pathname.startsWith(basePath)) {
    pathname = pathname.slice(basePath.length) || "/";
  }

  const relativePath = normalize(pathname).replace(/^([/\\])+/, "");
  let candidate = resolve(join(root, relativePath));

  if (!candidate.startsWith(root)) {
    response.writeHead(403);
    response.end("Forbidden");
    return;
  }

  if (existsSync(candidate) && statSync(candidate).isDirectory()) {
    candidate = join(candidate, "index.html");
  } else if (!extname(candidate)) {
    const htmlCandidate = `${candidate}.html`;
    const indexCandidate = join(candidate, "index.html");
    candidate = existsSync(htmlCandidate) ? htmlCandidate : indexCandidate;
  }

  if (!existsSync(candidate) || !statSync(candidate).isFile()) {
    response.writeHead(404);
    response.end("Not found");
    return;
  }

  response.writeHead(200, {
    "Cache-Control": "no-store",
    "Content-Type": contentTypes[extname(candidate)] ?? "application/octet-stream",
  });
  createReadStream(candidate).pipe(response);
}).listen(port, host, () => {
  process.stdout.write(`Static export listening at http://${host}:${port}${basePath}/\n`);
});
