import * as cdk from 'aws-cdk-lib';
import { Construct } from 'constructs';

import type { DeploymentStage } from './deployment-stage';
import { LambdaDependencies } from './lambda-dependencies';
import { MumbleApi } from './mumble-api';
import { UserTable } from './user-table';

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
    const userTable = new UserTable(this, 'UserTable', {
      deploymentStage,
    });
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
    // - user table name
    new cdk.CfnOutput(this, 'UserTableName', {
      description: 'Name of the DynamoDB table that stores user information',
      value: userTable.userTable.tableName,
    });
    // - prefix of the user private key paths
    new cdk.CfnOutput(this, 'UserPrivateKeyPathPrefix', {
      description: 'Path prefix of user private keys in Parameter Store on AWS Systems Manager',
      value: userTable.privateKeyPathPrefix,
    });
  }
}
