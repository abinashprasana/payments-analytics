import { defineConfig, globalIgnores } from "eslint/config";
import nextVitals from "eslint-config-next/core-web-vitals";
import nextTypeScript from "eslint-config-next/typescript";

export default defineConfig([
  ...nextVitals,
  ...nextTypeScript,
  // Generated output. Without these, `npm run lint` passes or fails depending
  // on whether you happened to build or run the browser suite first.
  globalIgnores([
    ".next/**",
    "node_modules/**",
    "next-env.d.ts",
    "out/**",
    "playwright-report/**",
    "test-results/**",
    ".lighthouse/**",
  ]),
]);
