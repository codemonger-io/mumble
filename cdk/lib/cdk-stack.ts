import * as cdk from 'aws-cdk-lib';
import { Construct } from 'constructs';

import type { DeploymentStage } from './deployment-stage';
import { LambdaDependencies } from './lambda-dependencies';

export interface Props extends cdk.StackProps {
  /** Deployment stage. */
  readonly deploymentStage: DeploymentStage;
}

export class CdkStack extends cdk.Stack {
  constructor(scope: Construct, id: string, props: Props) {
    super(scope, id, props);

    const lambdaDependencies = new LambdaDependencies(
      this,
      'LambdaDependencies',
    );
  }
}
