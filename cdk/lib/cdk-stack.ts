import {
  CfnOutput,
  Duration,
  RemovalPolicy,
  Stack,
  StackProps,
  aws_sqs as sqs,
} from 'aws-cdk-lib';
import { Construct } from 'constructs';

import type { DeploymentStage } from './deployment-stage';
import { LambdaDependencies } from './lambda-dependencies';
import { MumbleApi } from './mumble-api';
import { ObjectStore } from './object-store';
import { UserTable } from './user-table';

export interface Props extends StackProps {
  /** Deployment stage. */
  readonly deploymentStage: DeploymentStage;
}

export class CdkStack extends Stack {
  constructor(scope: Construct, id: string, props: Props) {
    super(scope, id, props);

    const { deploymentStage } = props;

    // common dead-letter queue
    const deadLetterQueue = new sqs.Queue(
      this,
      'DeadLetterQueue',
      {
        encryption: sqs.QueueEncryption.SQS_MANAGED,
        deliveryDelay: Duration.seconds(0),
        receiveMessageWaitTime: Duration.seconds(0),
        retentionPeriod: Duration.days(7),
        visibilityTimeout: Duration.seconds(60),
        removalPolicy: RemovalPolicy.RETAIN,
      },
    );

    const lambdaDependencies = new LambdaDependencies(
      this,
      'LambdaDependencies',
    );
    const userTable = new UserTable(this, 'UserTable', {
      deploymentStage,
    });
    const objectStore = new ObjectStore(this, 'ObjectStore', {
      deadLetterQueue,
    });
    const mumbleApi = new MumbleApi(this, 'MumbleApi', {
      deploymentStage,
      lambdaDependencies,
      objectStore,
      userTable,
    });

    // outputs
    // - Mumble API distribution domain name
    new CfnOutput(this, 'MumbleApiDistributionDomainName', {
      description: 'CloudFront distribution domain name of the Mumble endpoints API',
      value: mumbleApi.distribution.distributionDomainName,
    });
    // - user table name
    new CfnOutput(this, 'UserTableName', {
      description: 'Name of the DynamoDB table that stores user information',
      value: userTable.userTable.tableName,
    });
    // - prefix of the user private key paths
    new CfnOutput(this, 'UserPrivateKeyPathPrefix', {
      description: 'Path prefix of user private keys in Parameter Store on AWS Systems Manager',
      value: userTable.privateKeyPathPrefix,
    });
  }
}
