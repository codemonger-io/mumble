import * as path from 'path';
import {
  Duration,
  aws_lambda as lambda,
  aws_lambda_event_sources as eventsources,
  aws_sqs as sqs,
} from 'aws-cdk-lib';
import { Construct } from 'constructs';
import { PythonFunction } from '@aws-cdk/aws-lambda-python-alpha';

import type { LambdaDependencies } from './lambda-dependencies';
import type { ObjectStore } from './object-store';
import type { UserTable } from './user-table';

/** Properties for {@link Statistics}. */
export interface Props {
  /** Dependencies of Lambda functions. */
  readonly lambdaDependencies: LambdaDependencies;
  /** Dead letter queue. */
  readonly deadLetterQueue: sqs.IQueue;
  /** User table. */
  readonly userTable: UserTable;
  /** Object store. */
  readonly objectStore: ObjectStore;
}

/** CDK Construct that provisions Lambda functions to update statistics. */
export class Statistics extends Construct {
  constructor(scope: Construct, id: string, props: Props) {
    super(scope, id);

    const {
      deadLetterQueue,
      lambdaDependencies,
      objectStore,
      userTable,
    } = props;
    const { libActivityPub, libCommons, libMumble } = lambdaDependencies;

    // updates statistics on the user table.
    const updateUserStatisticsLambda = new PythonFunction(
      this,
      'UpdateUserStatisticsLmabda',
      {
        description: 'Updates statistics on the user table',
        runtime: lambda.Runtime.PYTHON_3_8,
        architecture: lambda.Architecture.ARM_64,
        entry: path.join('lambda', 'update_user_statistics'),
        index: 'index.py',
        handler: 'lambda_handler',
        layers: [libActivityPub, libCommons, libMumble],
        environment: {
          USER_TABLE_NAME: userTable.userTable.tableName,
        },
        memorySize: 256,
        timeout: Duration.seconds(30),
      },
    );
    userTable.userTable.grantReadWriteData(updateUserStatisticsLambda);
    userTable.grantBatchUpdateUserTable(updateUserStatisticsLambda);
    updateUserStatisticsLambda.addEventSource(
      new eventsources.DynamoEventSource(
        userTable.userTable,
        {
          startingPosition: lambda.StartingPosition.LATEST,
          batchSize: 10,
          maxBatchingWindow: Duration.seconds(1),
          onFailure: new eventsources.SqsDlq(deadLetterQueue),
          retryAttempts: 3,
        },
      ),
    );
    // updates statistics on the object table.
    const updateObjectStatisticsLambda = new PythonFunction(
      this,
      'UpdateObjectStatisticsLambda',
      {
        description: 'Updates statistics on the object table',
        runtime: lambda.Runtime.PYTHON_3_8,
        architecture: lambda.Architecture.ARM_64,
        entry: path.join('lambda', 'update_object_statistics'),
        index: 'index.py',
        handler: 'lambda_handler',
        layers: [libActivityPub, libCommons, libMumble],
        environment: {
          OBJECT_TABLE_NAME: objectStore.objectTable.tableName,
        },
        memorySize: 256,
        timeout: Duration.seconds(30),
      },
    );
    objectStore.objectTable.grantReadWriteData(updateObjectStatisticsLambda);
    objectStore.grantBatchUpdateObjectTable(updateObjectStatisticsLambda);
    updateObjectStatisticsLambda.addEventSource(
      new eventsources.DynamoEventSource(
        objectStore.objectTable,
        {
          startingPosition: lambda.StartingPosition.LATEST,
          batchSize: 10,
          maxBatchingWindow: Duration.seconds(1),
          onFailure: new eventsources.SqsDlq(deadLetterQueue),
          retryAttempts: 3,
        },
      ),
    );
  }
}
