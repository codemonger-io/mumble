import * as path from 'path';
import {
  Duration,
  aws_events as events,
  aws_events_targets as targets,
  aws_lambda as lambda,
  aws_sqs as sqs,
  aws_stepfunctions as stepfunctions,
  aws_stepfunctions_tasks as sfn_tasks,
} from 'aws-cdk-lib';
import { Construct } from 'constructs';
import { PythonFunction } from '@aws-cdk/aws-lambda-python-alpha';

import type { DeploymentStage } from './deployment-stage';
import type { LambdaDependencies } from './lambda-dependencies';
import type { ObjectStore } from './object-store';
import type { UserTable } from './user-table';

/** Properties for `Dispatcher`. */
export interface Props {
  /** Deployment stage. */
  readonly deploymentStage: DeploymentStage;
  /** Dependencies of Lambda functions. */
  readonly lambdaDependencies: LambdaDependencies;
  /** Dead letter queue. */
  readonly deadLetterQueue: sqs.IQueue;
  /** Object store that is the source of events. */
  readonly objectStore: ObjectStore;
  /** User table. */
  readonly userTable: UserTable;
}

/**
 * CDK construct that provisions Lambda functions and state machines
 * (workflows) to handle events.
 */
export class Dispatcher extends Construct {
  /**
   * Lambda function that translates an activity.
   * Implements a state in a workflow.
   */
  private translateActivityLambda: lambda.IFunction;

  constructor(scope: Construct, id: string, readonly props: Props) {
    super(scope, id);

    const {
      deadLetterQueue,
      deploymentStage,
      lambdaDependencies,
      objectStore,
      userTable,
    } = props;
    const { libActivityPub, libCommons, libMumble } = lambdaDependencies;

    // state Lambda functions
    // - translates an activity
    this.translateActivityLambda = new PythonFunction(
      this,
      'TranslateActivityLambda',
      {
        description: 'Translates an activity',
        runtime: lambda.Runtime.PYTHON_3_8,
        architecture: lambda.Architecture.ARM_64,
        entry: path.join('lambda', 'states', 'translate_activity'),
        index: 'index.py',
        handler: 'lambda_handler',
        layers: [libActivityPub, libCommons, libMumble],
        environment: {
          OBJECTS_BUCKET_NAME: objectStore.objectsBucket.bucketName,
          USER_TABLE_NAME: userTable.userTable.tableName,
        },
        memorySize: 256,
        timeout: Duration.seconds(30),
      },
    );
    objectStore.grantGetFromInbox(this.translateActivityLambda);
    userTable.userTable.grantReadWriteData(this.translateActivityLambda);

    // workflows
    // - dispatches a received activity
    const dispatchReceivedActivityWorkflow =
      this.createDispatchReceivedActivityWorkflow();
    objectStore.inboxObjectCreatedRule.addTarget(new targets.SfnStateMachine(
      dispatchReceivedActivityWorkflow,
      {
        input: events.RuleTargetInput.fromObject({
          activity: {
            bucket: events.EventField.fromPath('$.detail.bucket.name'),
            key: events.EventField.fromPath('$.detail.object.key'),
          },
        }),
        deadLetterQueue,
      },
    ));
  }

  // Creates a workflow that dispatches a received activity.
  private createDispatchReceivedActivityWorkflow():
    stepfunctions.IStateMachine
  {
    const { deploymentStage } = this.props;
    const workflowId = `DispatchReceivedActivity_${deploymentStage}`;

    // defines states
    // - translates an activity
    const invokeTranslateActivity = new sfn_tasks.LambdaInvoke(
      this,
      `TranslateActivity_${workflowId}`,
      {
        lambdaFunction: this.translateActivityLambda,
        comment: 'Invokes TranslateActivityLambda',
        payloadResponseOnly: true,
        taskTimeout: stepfunctions.Timeout.duration(Duration.seconds(30)),
        retryOnServiceExceptions: true,
      },
    );

    // builds the state machine
    return new stepfunctions.StateMachine(this, workflowId, {
      definition: invokeTranslateActivity,
      timeout: Duration.minutes(30),
    });
  }
}
