import { nodeServerAdapter } from "@builder.io/qwik-city/adapters/node-server/vite";
import { extendConfig } from "@builder.io/qwik-city/vite";
import baseConfig from "../../vite.config";
import { builtinModules } from "module";

const awsSdkModules = [
  '@aws-sdk/client-dynamodb',
  '@aws-sdk/client-s3',
  '@aws-sdk/client-ssm',
  '@aws-sdk/lib-dynamodb',
];

export default extendConfig(baseConfig, () => {
  return {
    ssr: {
      // This configuration will bundle all dependencies, except the node builtins (path, fs, etc.)
      external: [
        ...builtinModules,
        ...awsSdkModules,
      ],
      noExternal: /./,
    },
    build: {
      target: 'esnext', // we need the top-level await
      minify: false,
      ssr: true,
      rollupOptions: {
        input: ["./src/entry_aws-lambda.tsx", "@qwik-city-plan"],
      },
    },
    plugins: [nodeServerAdapter({ name: "aws-lambda" })],
  };
});
