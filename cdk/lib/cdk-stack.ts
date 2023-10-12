import {
  CfnOutput,
  Duration,
  Fn,
  RemovalPolicy,
  Stack,
  StackProps,
  aws_sqs as sqs,
} from 'aws-cdk-lib';
import { Construct } from 'constructs';

import type { DeploymentStage } from './deployment-stage';
import { Dispatcher } from './dispatcher';
import { Indexer } from './indexer';
import { LambdaDependencies } from './lambda-dependencies';
import { MumbleApi } from './mumble-api';
import { ObjectStore } from './object-store';
import { Statistics } from './statistics';
import { SystemParameters } from './system-parameters';
import { UserPool } from './user-pool';
import { UserTable } from './user-table';
import { Viewer } from './viewer';

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
    const userPool = new UserPool(this, 'UserPool', {
      deploymentStage,
      objectStore,
    });
    const dispatcher = new Dispatcher(this, 'Dispatcher', {
      deadLetterQueue,
      deploymentStage,
      lambdaDependencies,
      objectStore,
      systemParameters,
      userTable,
    });
    const indexer = new Indexer(this, 'Indexer');
    const viewer = new Viewer(this, 'Viewer', {
      indexer,
      objectStore,
      systemParameters,
      userTable,
    });
    const mumbleApi = new MumbleApi(this, 'MumbleApi', {
      deploymentStage,
      lambdaDependencies,
      objectStore,
      systemParameters,
      userPool,
      userTable,
      viewer,
    });
    const statistics = new Statistics(this, 'Statistics', {
      deadLetterQueue,
      lambdaDependencies,
      objectStore,
      userTable,
    });

    // outputs
    new CfnOutput(this, 'MumbleApiDistributionDomainName', {
      description: 'CloudFront distribution domain name of the Mumble endpoints API',
      value: mumbleApi.distribution.distributionDomainName,
    });
    new CfnOutput(this, 'UserPoolId', {
      description: 'ID of the user pool',
      value: userPool.userPool.userPoolId,
    });
    new CfnOutput(this, 'UserPoolHostedUiClientId', {
      description: 'ID of the user pool client with the hosted UI',
      value: userPool.hostedUiClient.userPoolClientId,
    });
    new CfnOutput(this, 'UserPoolDomainName', {
      description: 'Domain name of the user pool',
      value: Fn.join('', [
        userPool.userPoolDomain.domainName,
        '.auth.',
        Stack.of(this).region,
        '.amazoncognito.com',
      ]),
    });
    new CfnOutput(this, 'IdentityPoolId', {
      description: 'ID of the identity pool',
      value: userPool.identityPoolId,
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
    new CfnOutput(this, 'ObjectTableName', {
      description: 'Name of the DynamoDB table that stores objects',
      value: objectStore.objectTable.tableName,
    });
    new CfnOutput(this, 'DomainNameParameterPath', {
      description: 'Path to the domain name stored in Parameter Store on AWS Systems Manager',
      value: systemParameters.domainNameParameter.parameterName,
    });
    new CfnOutput(this, 'OpenAiApiKeyParameterPath', {
      description: 'Path to the OpenAI API key stored in Parameter Store on AWS Systems Manager',
      value: systemParameters.openAiApiKeyParameter.parameterName,
    });
    new CfnOutput(this, 'IndexerDatabaseBucketName', {
      description: 'Name of the S3 bucket that stores the databases for the indexer',
      value: indexer.databaseBucket.bucketName,
    });
    new CfnOutput(this, 'SearchSimilarMumblingsFunctionName', {
      description: 'Name of the Lambda function that searches similar mumblings',
      value: indexer.searchSimilarLambda.functionName,
    });
  }
}
