import * as cdk from 'aws-cdk-lib';
import { Construct } from 'constructs';

import type { DeploymentStage } from './deployment-stage';
import { LambdaDependencies } from './lambda-dependencies';
import { MumbleApi } from './mumble-api';

export interface Props extends cdk.StackProps {
  /** Deployment stage. */
  readonly deploymentStage: DeploymentStage;
}

export class CdkStack extends cdk.Stack {
  constructor(scope: Construct, id: string, props: Props) {
    super(scope, id, props);

    const { deploymentStage } = props;

    const lambdaDependencies = new LambdaDependencies(
      this,
      'LambdaDependencies',
    );
    const mumbleApi = new MumbleApi(this, 'MumbleApi', {
      deploymentStage,
      lambdaDependencies,
    });

    // outputs
    // - Mumble API distribution domain name
    new cdk.CfnOutput(this, 'MumbleApiDistributionDomainName', {
      description: 'CloudFront distribution domain name of the Mumble endpoints API',
      value: mumbleApi.distribution.distributionDomainName,
    });
  }
}
