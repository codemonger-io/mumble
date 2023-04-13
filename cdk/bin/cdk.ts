#!/usr/bin/env node
import 'source-map-support/register';
import * as cdk from 'aws-cdk-lib';
import { CdkStack } from '../lib/cdk-stack';

import { getDeploymentStage } from '../lib/deployment-stage';

const app = new cdk.App();
const deploymentStage = getDeploymentStage(app.node);
new CdkStack(app, `mumble-${deploymentStage}`, {
  env: {
    account: process.env.CDK_DEFAULT_ACCOUNT,
    region: process.env.CDK_DEFAULT_REGION,
  },
  deploymentStage,
  tags: {
    project: 'mumble',
  },
});
