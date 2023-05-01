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
import type { SystemParameters } from './system-parameters';
import type { UserTable } from './user-table';

/** Properties for `Dispatcher`. */
export interface Props {
  /** Deployment stage. */
  readonly deploymentStage: DeploymentStage;
  /** System parameters. */
  readonly systemParameters: SystemParameters;
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
   * Lambda function that translates an activity receinved in the inbox.
   * Implements a state in a workflow.
   */
  private translateActivityLambda: lambda.IFunction;
  /**
   * Lambda function that translates an outbound object in the staging outbox.
   * Implements a state in a workflow.
   */
  private translateOutboundObjectLambda: lambda.IFunction;
  /**
   * Lambda function that plans delivery of a staged activity.
   * Implements a state in a workflow.
   */
  private planActivityDeliveryLambda: lambda.IFunction;
  /**
   * Lambda function that delivers an activity to a single recipient.
   * Implements a state in a workflow.
   */
  private deliverActivityLambda: lambda.IFunction;

  constructor(scope: Construct, id: string, readonly props: Props) {
    super(scope, id);

    const {
      deadLetterQueue,
      deploymentStage,
      lambdaDependencies,
      objectStore,
      systemParameters,
      userTable,
    } = props;
    const { libActivityPub, libCommons, libMumble } = lambdaDependencies;

    // state Lambda functions
    // - translates an activity received in the inbox
    this.translateActivityLambda = new PythonFunction(
      this,
      'TranslateActivityLambda',
      {
        description: 'Translates an activity received in the inbox',
        runtime: lambda.Runtime.PYTHON_3_8,
        architecture: lambda.Architecture.ARM_64,
        entry: path.join('lambda', 'states', 'translate_activity'),
        index: 'index.py',
        handler: 'lambda_handler',
        layers: [libActivityPub, libCommons, libMumble],
        environment: {
          OBJECTS_BUCKET_NAME: objectStore.objectsBucket.bucketName,
          USER_TABLE_NAME: userTable.userTable.tableName,
          DOMAIN_NAME_PARAMETER_PATH:
            systemParameters.domainNameParameter.parameterName,
        },
        memorySize: 256,
        timeout: Duration.seconds(30),
      },
    );
    objectStore.grantGetFromInbox(this.translateActivityLambda);
    objectStore.grantPutIntoStagingOutbox(this.translateActivityLambda);
    userTable.userTable.grantReadWriteData(this.translateActivityLambda);
    systemParameters.domainNameParameter.grantRead(
      this.translateActivityLambda,
    );
    // - translates an outbound object in the staging outbox
    this.translateOutboundObjectLambda = new PythonFunction(
      this,
      'TranslateOutboundObjectLambda',
      {
        description: 'Stages an outbound object in the staging outbox',
        runtime: lambda.Runtime.PYTHON_3_8,
        architecture: lambda.Architecture.ARM_64,
        entry: path.join('lambda', 'states', 'translate_outbound_object'),
        index: 'index.py',
        handler: 'lambda_handler',
        layers: [libActivityPub, libCommons, libMumble],
        environment: {
          OBJECTS_BUCKET_NAME: objectStore.objectsBucket.bucketName,
          USER_TABLE_NAME: userTable.userTable.tableName,
          DOMAIN_NAME_PARAMETER_PATH:
            systemParameters.domainNameParameter.parameterName,
        },
        memorySize: 256,
        timeout: Duration.seconds(30),
      },
    );
    userTable.userTable.grantReadData(this.translateOutboundObjectLambda);
    objectStore.grantGetFromStagingOutbox(this.translateOutboundObjectLambda);
    objectStore.grantPutIntoOutbox(this.translateOutboundObjectLambda);
    objectStore.grantPutIntoObjectsFolder(this.translateOutboundObjectLambda);
    systemParameters.domainNameParameter.grantRead(
      this.translateOutboundObjectLambda,
    );
    // - plans delivery of a staged activity
    this.planActivityDeliveryLambda = new PythonFunction(
      this,
      'PlanActivityDeliveryLambda',
      {
        description: 'Plans delivery of a staged activity',
        runtime: lambda.Runtime.PYTHON_3_8,
        architecture: lambda.Architecture.ARM_64,
        entry: path.join('lambda', 'states', 'plan_activity_delivery'),
        index: 'index.py',
        handler: 'lambda_handler',
        layers: [libActivityPub, libCommons, libMumble],
        environment: {
          OBJECTS_BUCKET_NAME: objectStore.objectsBucket.bucketName,
          USER_TABLE_NAME: userTable.userTable.tableName,
          DOMAIN_NAME_PARAMETER_PATH:
            systemParameters.domainNameParameter.parameterName,
        },
        memorySize: 256,
        timeout: Duration.minutes(15),
      },
    );
    userTable.userTable.grantReadData(this.planActivityDeliveryLambda);
    objectStore.grantGetFromOutbox(this.planActivityDeliveryLambda);
    systemParameters.domainNameParameter.grantRead(
      this.planActivityDeliveryLambda,
    );
    // - delivers an activity to a single recipient
    this.deliverActivityLambda = new PythonFunction(
      this,
      'DeliverActivityLambda',
      {
        description: 'Delivers an activity to a single recipient',
        runtime: lambda.Runtime.PYTHON_3_8,
        architecture: lambda.Architecture.ARM_64,
        entry: path.join('lambda', 'states', 'deliver_activity'),
        index: 'index.py',
        handler: 'lambda_handler',
        layers: [libActivityPub, libCommons, libMumble],
        environment: {
          OBJECTS_BUCKET_NAME: objectStore.objectsBucket.bucketName,
          USER_TABLE_NAME: userTable.userTable.tableName,
          DOMAIN_NAME_PARAMETER_PATH:
            systemParameters.domainNameParameter.parameterName,
        },
        memorySize: 256,
        timeout: Duration.seconds(30),
      },
    );
    objectStore.grantGetFromOutbox(this.deliverActivityLambda);
    userTable.userTable.grantReadData(this.deliverActivityLambda);
    userTable.grantReadPrivateKeys(this.deliverActivityLambda);
    systemParameters.domainNameParameter.grantRead(this.deliverActivityLambda);

    // workflows
    const s3ObjectInput = {
      bucket: events.EventField.fromPath('$.detail.bucket.name'),
      key: events.EventField.fromPath('$.detail.object.key'),
    };
    // - dispatches a received activity
    const dispatchReceivedActivityWorkflow =
      this.createDispatchReceivedActivityWorkflow();
    objectStore.inboxObjectCreatedRule.addTarget(new targets.SfnStateMachine(
      dispatchReceivedActivityWorkflow,
      {
        input: events.RuleTargetInput.fromObject({
          activity: s3ObjectInput,
        }),
        deadLetterQueue,
      },
    ));
    // - translate an outbound object in the staging outbox
    const translateOutboundObjectWorkflow =
      this.createTranslateOutboundObjectWorkflow();
    objectStore.stagingOutboxObjectCreatedRule.addTarget(
      new targets.SfnStateMachine(
        translateOutboundObjectWorkflow,
        {
          input: events.RuleTargetInput.fromObject({
            'object': s3ObjectInput,
          }),
          deadLetterQueue,
        },
      ),
    );
    // - delivers a staged activity in the outbox
    const deliverStagedActivityWorkflow =
      this.createDeliverStagedActivityWorkflow();
    objectStore.outboxObjectCreatedRule.addTarget(new targets.SfnStateMachine(
      deliverStagedActivityWorkflow,
      {
        input: events.RuleTargetInput.fromObject({
          activity: s3ObjectInput,
        }),
        deadLetterQueue,
      },
    ));
  }

  // Creates a workflow that dispatches a received activity.
  //
  // The workflow supposes an input is like:
  //
  // {
  //   activity: {
  //     bucket: '<bucket-name>',
  //     key: '<object-key>'
  //   }
  // }
  private createDispatchReceivedActivityWorkflow():
    stepfunctions.IStateMachine
  {
    const { deploymentStage } = this.props;
    const workflowId = `DispatchReceivedActivity_${deploymentStage}`;

    // defines states
    // - translates an activity received in the inbox
    const invokeTranslateActivity = new sfn_tasks.LambdaInvoke(
      this,
      `TranslateActivity_${workflowId}`,
      {
        lambdaFunction: this.translateActivityLambda,
        comment: 'Invokes TranslateActivityLambda',
        payloadResponseOnly: true,
        taskTimeout: stepfunctions.Timeout.duration(Duration.seconds(30)),
      },
    );

    // builds the state machine
    return new stepfunctions.StateMachine(this, workflowId, {
      definition: invokeTranslateActivity,
      timeout: Duration.minutes(30),
    });
  }

  // Creates a workflow that stages an object in the staging folder.
  //
  // The workflow supposes the input is like:
  //
  // {
  //   object: {
  //     bucket: '<bucket-name>',
  //     key: '<object-key>'
  //   }
  // }
  private createTranslateOutboundObjectWorkflow():
    stepfunctions.IStateMachine
  {
    const { deploymentStage } = this.props;
    const workflowId = `TranslateOutboundObject_${deploymentStage}`;

    // defines states
    // - translate an outbound object in the staging outbox
    const invokeTranslateOutboundObject = new sfn_tasks.LambdaInvoke(
      this,
      `TranslateOutboundObject_${workflowId}`,
      {
        lambdaFunction: this.translateOutboundObjectLambda,
        comment: 'Invokes TranslateOutboundObjectLambda',
        payloadResponseOnly: true,
        taskTimeout: stepfunctions.Timeout.duration(Duration.seconds(30)),
      },
    );

    // builds the state machine
    return new stepfunctions.StateMachine(this, workflowId, {
      definition: invokeTranslateOutboundObject,
      timeout: Duration.minutes(5),
    });
  }

  // Creates a workflow that delivers a staged activity.
  //
  // The workflow supposes the input is like:
  //
  // {
  //   activity: {
  //     bucket: '<bucket-name>',
  //     key: '<object-key>'
  //   }
  // }
  private createDeliverStagedActivityWorkflow(): stepfunctions.IStateMachine {
    const { deploymentStage } = this.props;
    const workflowId = `DeliverStagedActivity_${deploymentStage}`;

    // defines states
    // - plans the delivery; i.e., resolve recipients' inboxes
    const invokePlanActivityDelivery = new sfn_tasks.LambdaInvoke(
      this,
      `PlanActivityDelivery_${workflowId}`,
      {
        lambdaFunction: this.planActivityDeliveryLambda,
        comment: 'Invokes PlanActivityDeliveryLambda',
        payloadResponseOnly: true,
        taskTimeout: stepfunctions.Timeout.duration(Duration.minutes(15)),
      },
    );
    // - delivers the activity to each recipient
    const forEachRecipient = new stepfunctions.Map(
      this,
      `ForEachRecipient_${workflowId}`,
      {
        comment: 'For each recipient',
        maxConcurrency: 10,
        itemsPath: stepfunctions.JsonPath.stringAt('$.recipients'),
        parameters: {
          'activity.$': '$$.Execution.Input.activity',
          'recipient.$': '$$.Map.Item.Value',
        },
      },
    );
    const invokeDeliverActivity = new sfn_tasks.LambdaInvoke(
      this,
      `DeliverActivity_${workflowId}`,
      {
        lambdaFunction: this.deliverActivityLambda,
        comment: 'Delivers an activity to a single recipient',
        payloadResponseOnly: true,
        taskTimeout: stepfunctions.Timeout.duration(Duration.seconds(30)),
      },
    );
    forEachRecipient.iterator(invokeDeliverActivity);

    // builds the state machine
    return new stepfunctions.StateMachine(this, workflowId, {
      definition: invokePlanActivityDelivery.next(forEachRecipient),
      timeout: Duration.hours(1),
    });
  }
}
