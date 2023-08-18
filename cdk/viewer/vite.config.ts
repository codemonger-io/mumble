import { defineConfig } from "vite";
import { qwikVite } from "@builder.io/qwik/optimizer";
import { qwikCity } from "@builder.io/qwik-city/vite";
import tsconfigPaths from "vite-tsconfig-paths";

export default defineConfig(() => {
  let base = process.env.DISTRIBUTION_BASEPATH ?? '/';
  if (!base.endsWith('/')) {
    console.warn(`DISTRIBUTION_BASEPATH '${base}' should end with '/'`);
    base += '/';
  }

  return {
    base,
    plugins: [qwikCity(), qwikVite(), tsconfigPaths()],
    preview: {
      headers: {
        "Cache-Control": "public, max-age=600",
      },
    },
  };
});
