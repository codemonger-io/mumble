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
import { Dispatcher } from './dispatcher';
import { LambdaDependencies } from './lambda-dependencies';
import { MumbleApi } from './mumble-api';
import { ObjectStore } from './object-store';
import { SystemParameters } from './system-parameters';
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
    const deadLetterQueue = new sqs.Queue(this, 'DeadLetterQueue', {
      deliveryDelay: Duration.seconds(0),
      receiveMessageWaitTime: Duration.seconds(0),
      visibilityTimeout: Duration.minutes(1),
      retentionPeriod: Duration.days(7),
      encryption: sqs.QueueEncryption.SQS_MANAGED,
    });

    const systemParameters = new SystemParameters(this, 'SystemParameters');
    const lambdaDependencies = new LambdaDependencies(
      this,
      'LambdaDependencies',
    );
    const userTable = new UserTable(this, 'UserTable', {
      deploymentStage,
    });
    const objectStore = new ObjectStore(this, 'ObjectStore', {
      deploymentStage,
    });
    const dispatcher = new Dispatcher(this, 'Dispatcher', {
      deadLetterQueue,
      deploymentStage,
      lambdaDependencies,
      objectStore,
      systemParameters,
      userTable,
    });
    const mumbleApi = new MumbleApi(this, 'MumbleApi', {
      deploymentStage,
      lambdaDependencies,
      objectStore,
      systemParameters,
      userTable,
    });

    // outputs
    new CfnOutput(this, 'MumbleApiDistributionDomainName', {
      description: 'CloudFront distribution domain name of the Mumble endpoints API',
      value: mumbleApi.distribution.distributionDomainName,
    });
    new CfnOutput(this, 'ObjectsBucketName', {
      description: 'Name of the S3 bucket that stores objects',
      value: objectStore.objectsBucket.bucketName,
    });
    new CfnOutput(this, 'UserTableName', {
      description: 'Name of the DynamoDB table that stores user information',
      value: userTable.userTable.tableName,
    });
    new CfnOutput(this, 'UserPrivateKeyPathPrefix', {
      description: 'Path prefix of user private keys in Parameter Store on AWS Systems Manager',
      value: userTable.privateKeyPathPrefix,
    });
    new CfnOutput(this, 'DomainNameParameterPath', {
      description: 'Path to the domain name stored in Parameter Store on AWS Systems Manager',
      value: systemParameters.domainNameParameter.parameterName,
    });
  }
}
