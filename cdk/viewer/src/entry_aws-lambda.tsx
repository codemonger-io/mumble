/*
 * WHAT IS THIS FILE?
 *
 * It's the entry point for the Express HTTP server when building for production.
 *
 * Learn more about Node.js server integrations here:
 * - https://qwik.builder.io/docs/deployments/node/
 *
 */
import "source-map-support/register";
import {
  createQwikCity,
  type PlatformNode,
} from "@builder.io/qwik-city/middleware/node";
import qwikCityPlan from "@qwik-city-plan";
import { manifest } from "@qwik-client-manifest";
import serverless from "serverless-http";
import { GetParameterCommand, SSMClient } from "@aws-sdk/client-ssm";
import render from "./entry.ssr";

declare global {
  interface QwikCityPlatform extends PlatformNode {}
}

// optionally obtains the domain name from the Parameter Store on SSM
async function getDomainNameParameter(): Promise<string | null> {
  const parameterName = process.env.DOMAIN_NAME_PARAMETER_PATH;
  console.log("obtaining domain name from Parameter Store", parameterName);
  if (parameterName == null) {
    console.log("no domain name parameter configured");
    return null;
  }
  const ssm = new SSMClient({});
  const res = await ssm.send(new GetParameterCommand({
    Name: parameterName,
    WithDecryption: true,
  }));
  // service should not start with a bad configuration
  return res.Parameter?.Value ?? null;
}

const DOMAIN_NAME = await getDomainNameParameter();
console.log("DOMAIN_NAME", DOMAIN_NAME);

// Create the Qwik City router
const { router, notFound, staticFile } = createQwikCity({
  render,
  qwikCityPlan,

  manifest,
  static: {
    cacheControl: "public, max-age=31557600",
  },
  getOrigin(req) {
    if (process.env.IS_OFFLINE) {
      return `http://${req.headers.host}`;
    }
    if (DOMAIN_NAME != null) {
      return `https://${DOMAIN_NAME}`;
    }
    return null;
  },
});

export const qwikApp = serverless(
  {
    handle: (req: any, res: any) => {
      req.url = fixPath(req.url);
      staticFile(req, res, () => {
        router(req, res, () => {
          notFound(req, res, () => {});
        });
      });
    },
  },
  {
    binary: true,
  },
);

function fixPath(path: string) {
  if (qwikCityPlan.trailingSlash) {
    const url = new URL(path, "http://aws-qwik.local");
    if (url.pathname.includes(".", url.pathname.lastIndexOf("/"))) {
      return path;
    }
    if (!url.pathname.endsWith("/")) {
      return url.pathname + "/" + url.search;
    }
  }
  return path;
}
