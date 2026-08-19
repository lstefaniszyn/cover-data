import { defineConfig } from "vitest/config";
import { fileURLToPath } from "url";
import path from "path";

const __dirname = fileURLToPath(new URL(".", import.meta.url));

export default defineConfig({
  resolve: {
    alias: {
      "@": path.join(__dirname, "src"),
      // Astro virtual modules are not available in the Node test environment.
      // These stubs export undefined for every env var so pure-logic tests can
      // import modules that transitively touch astro:env without blowing up.
      "astro:env/server": path.join(__dirname, "src/__test-utils__/astro-env-server.stub.ts"),
      "astro:env/client": path.join(__dirname, "src/__test-utils__/astro-env-client.stub.ts"),
    },
  },
  test: {
    environment: "node",
    include: ["src/**/*.{test,spec}.ts"],
    globals: true,
  },
});
