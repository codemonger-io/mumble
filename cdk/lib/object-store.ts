import {
  Duration,
  RemovalPolicy,
  Stack,
  aws_dynamodb as dynamodb,
  aws_events as events,
  aws_iam as iam,
  aws_s3 as s3,
} from 'aws-cdk-lib';
import { Construct } from 'constructs';

import type { DeploymentStage } from './deployment-stage';

/** Paht prefix of the inbox. */
export const INBOX_PREFIX = 'inbox/';
/** Path prefix of the outbox. */
export const OUTBOX_PREFIX = 'outbox/';
/**
 * Path prefix of the staging outbox.
 *
 * @remarks
 *
 * The staging outbox is the folder where objects are pushed before sending
 * through the outbox.
 *
 * The staging outbox provides an opportunity to arrange an object before
 * sending it; e.g., assigning an ID, timestamping.
 */
export const STAGING_OUTBOX_PREFIX = 'staging/';
/** Path prefix of the objects folder. */
export const OBJECTS_FOLDER_PREFIX = 'objects/';
/** Path prefix of the media folder. */
export const MEDIA_FOLDER_PREFIX = 'media/';

/** Properties for {@link ObjectStore}. */
export interface Props {
  /** Deployment stage. */
  readonly deploymentStage: DeploymentStage;
}

/**
 * CDK construct that provisions the S3 bucket for objects.
 *
 * @remarks
 *
 * #### Inbox
 *
 * The inbox (`inbox`) folder stores activities received from other servers.
 *
 * Every user `{username}` has a dedicated folder in the inbox folder:
 * `inbox/users/{username}`
 *
 * I am planning to allocate the shared inbox at `inbox/shared`.
 *
 * #### Staging outbox
 *
 * The staging outbox (`staging`) folder stores activities to be delivered to
 * other servers.
 *
 * Every user `{username}` has a dedicated folder in the staging outbox folder:
 * `staging/users/{username}`
 *
 * #### Outbox
 *
 * The outbox (`outbox`) folder stores activities made by a specifi user.
 *
 * Every user `{username}` has a dedicated folder in the oubtox folder:
 * `outbox/users/{username}`
 *
 * #### Objects
 *
 * The objects (`objects`) folder stores non-activity objects.
 *
 * Every user `{username}` has a dedicated folder in the objects folder:
 * `objects/users/{username}`
 *
 * I am planning to further split folders in user's folder:
 * - `objects/users/{username}/posts`: for posts
 * - `objects/users/{username}/media`: for private media files (TBC)
 *
 * #### Media
 *
 * The media (`media`) folder stores public media files; e.g., images, videos.
 *
 * Every user `{username}` has a dedicated folder in the media folder:
 * `media/users/{username}`
 */
export class ObjectStore extends Construct {
  /** S3 bucket for objects. */
  readonly objectsBucket: s3.IBucket;
  /** DynamoDB table to manage metadata and the history of objects. */
  readonly objectTable: dynamodb.Table;
  /**
   * EventBridge rule that triggers when a new object is created in the inbox
   * folder in the S3 bucekt.
   *
   * @remarks
   *
   * Please add a target to handle events.
   */
  readonly inboxObjectCreatedRule: events.Rule;
  /**
   * EventBridge rule that triggers when a new object is created in the staging
   * outbox folder in the S3 bucket.
   *
   * @remarks
   *
   * Please add a target to handle events.
   */
  readonly stagingOutboxObjectCreatedRule: events.Rule;
  /**
   * EventBridge rule that triggers when a new object is created in the outbox
   * folder in the S3 bucket.
   *
   * @remarks
   *
   * Please add a target to handle events.
   */
  readonly outboxObjectCreatedRule: events.Rule;
  /**
   * EventBridge rule that triggers when a new object is created in the objects
   * folder in the S3 bucket.
   *
   * @remarks
   *
   * Please add a target to handle events.
   */
  readonly objectsFolderObjectCreatedRule: events.Rule;

  constructor(scope: Construct, id: string, props: Props) {
    super(scope, id);

    const { deploymentStage } = props;

    // S3 bucket for objects
    this.objectsBucket = new s3.Bucket(this, 'ObjectsBucket', {
      blockPublicAccess: s3.BlockPublicAccess.BLOCK_ALL,
      encryption: s3.BucketEncryption.S3_MANAGED,
      eventBridgeEnabled: true,
      cors: [
        {
          allowedMethods: [
            s3.HttpMethods.GET,
            s3.HttpMethods.PUT,
          ],
          allowedOrigins: ['*'], // TODO: limit for production
          allowedHeaders: ['*'],
        },
      ],
      removalPolicy: RemovalPolicy.RETAIN,
    });

    // DynamoDB table to manage metadata and the history of objects
    const billingSettings = deploymentStage === 'production' ? {
      billingMode: dynamodb.BillingMode.PAY_PER_REQUEST,
    } : {
      billingMode: dynamodb.BillingMode.PROVISIONED,
      readCapacity: 2,
      writeCapacity: 2,
    };
    this.objectTable = new dynamodb.Table(this, 'ObjectTable', {
      // primary key pattern
      //
      // 1. metadata of an activity
      //     - pk: "activity:<username>:<yyyy-mm>"
      //         - `<yyyy-mm>` is the year and month of the creation
      //     - sk: "<ddTHH:MM:ss.SSSSSS>:<unique-part>"
      //         - `<ddTHH:MM:ss.SSSSSS>` is the date and time of the creation
      //         - `<unique-part>` is the unique part of the activity ID
      //
      //    non-key attributes
      //     - id: "<object-id>"
      //     - type: "<activity-type>"
      //     - username: "<username>"
      //     - category: "<category>"
      //     - published: "<yyyy-mm-ddTHH:MM:ssZ>"
      //     - createdAt: "<yyyy-mm-ddTHH:MM:ss.SSSSSSZ>"
      //         - may be different from `published`
      //     - updatedAt: "<yyyy-mm-ddTHH:MM:ss.SSSSSSZ>"
      //     - isPublic: whether the activity is public
      //
      // 2. metadata of an object
      //     - pk: "object:<username>:<category>:<unique-part>"
      //         - `<category>` may be "post" or "media"
      //     - sk: "metadata"
      //
      //    non-key attributes
      //     - id: "<object-id>"
      //     - type: "<object-type>"
      //     - username: "<username>"
      //     - category: "<category>"
      //     - published: "<yyyy-mm-ddTHH:MM:ssZ>"
      //     - createdAt: "<yyyy-mm-ddTHH:MM:ss.SSSSSSZ>"
      //         - may be different from `published`
      //     - updatedAt: "<yyyy-mm-ddTHH:MM:ss.SSSSSSZ>"
      //     - isPublic: whether the object is public
      //     - replyCount: 123
      //
      // 3. metadata of a reply to an object
      //     - pk: "object:<username>:<category>:<unique-part>"
      //     - sk: "reply:<yyyy-mm-ddTHH:MM:ssZ>:<reply-object-id>"
      //         - `<yyyy-mm-ddTHH:MM:ssZ>` is the published datetime of the
      //           reply
      //
      //    non-key attributes
      //     - id: "<reply-object-id>"
      //     - category: 'reply'
      //     - published: "<yyyy-mm-ddTHH:MM:ssZ>"
      //     - isPublic: whether the reply is public
      partitionKey: {
        name: 'pk',
        type: dynamodb.AttributeType.STRING,
      },
      sortKey: {
        name: 'sk',
        type: dynamodb.AttributeType.STRING,
      },
      stream: dynamodb.StreamViewType.KEYS_ONLY,
      removalPolicy: RemovalPolicy.RETAIN,
      ...billingSettings,
    });

    // S3 notification events should be sent to the default event bus
    const eventBus = events.EventBus.fromEventBusName(
      this,
      'DefaultEventBus',
      'default',
    );

    // EventBridge rules
    // - triggers when a new object is created in the inbox
    this.inboxObjectCreatedRule = new events.Rule(
      this,
      'InboxObjectCreatedRule',
      {
        description: 'Triggers when a new object is created in the inbox folder in the S3 bucket',
        eventBus,
        enabled: true,
        eventPattern: this.objectCreatedEventPattern(INBOX_PREFIX),
      },
    );
    // - triggers when a new object is created in the staging outbox
    this.stagingOutboxObjectCreatedRule = new events.Rule(
      this,
      'StagingOutboxObjectCreatedRule',
      {
        description: 'Triggers when a new object is created in the staging outbox folder in the S3 bucket',
        eventBus,
        enabled: true,
        eventPattern: this.objectCreatedEventPattern(STAGING_OUTBOX_PREFIX),
      },
    );
    // - triggers when a new object is created in the outbox
    this.outboxObjectCreatedRule = new events.Rule(
      this,
      'OutboxObjectCreatedRule',
      {
        description: 'Triggers when a new object is created in the outbox folder in the S3 bucket',
        eventBus,
        enabled: true,
        eventPattern: this.objectCreatedEventPattern(OUTBOX_PREFIX),
      },
    );
    // - triggers when a new object is created in the objects folder
    this.objectsFolderObjectCreatedRule = new events.Rule(
      this,
      'ObjectsFolderObjectCreatedRule',
      {
        description: 'Triggers when a new object is created in the objects folder in the S3 bucket',
        eventBus,
        enabled: true,
        eventPattern: this.objectCreatedEventPattern(OBJECTS_FOLDER_PREFIX),
      },
    );
  }

  /** Grants a given principal "Put" access to the inbox. */
  grantPutIntoInbox(grantee: iam.IGrantable): iam.Grant {
    return this.objectsBucket.grantPut(grantee, INBOX_PREFIX + '*');
  }

  /** Grants a given principal "Get" access from the inbox. */
  grantGetFromInbox(grantee: iam.IGrantable): iam.Grant {
    return this.objectsBucket.grantRead(grantee, INBOX_PREFIX + '*');
  }

  /** Grants a given principal "Put" access to the outbox. */
  grantPutIntoOutbox(grantee: iam.IGrantable): iam.Grant {
    return this.objectsBucket.grantPut(grantee, OUTBOX_PREFIX + '*');
  }

  /** Grants a given principal "Get" access from the outbox. */
  grantGetFromOutbox(grantee: iam.IGrantable): iam.Grant {
    return this.objectsBucket.grantRead(grantee, OUTBOX_PREFIX + '*');
  }

  /** Grants a given principal "Put" access to the staging outbox. */
  grantPutIntoStagingOutbox(grantee: iam.IGrantable): iam.Grant {
    return this.objectsBucket.grantPut(grantee, STAGING_OUTBOX_PREFIX + '*');
  }

  /** Grants a given principal "Get" access from the staging outbox. */
  grantGetFromStagingOutbox(grantee: iam.IGrantable): iam.Grant {
    return this.objectsBucket.grantRead(grantee, STAGING_OUTBOX_PREFIX + '*');
  }

  /** Grants a given principal "Put" access to the objects folder. */
  grantPutIntoObjectsFolder(grantee: iam.IGrantable): iam.Grant {
    return this.objectsBucket.grantPut(grantee, OBJECTS_FOLDER_PREFIX + '*');
  }

  /** Grants a given principal "Get" access from the objects folder. */
  grantGetFromObjectsFolder(grantee: iam.IGrantable): iam.Grant {
    return this.objectsBucket.grantRead(grantee, OBJECTS_FOLDER_PREFIX + '*');
  }

  /** Grants a given principal batch update on the object table. */
  grantBatchUpdateObjectTable(grantee: iam.IGrantable): iam.Grant {
    return iam.Grant.addToPrincipal({
      grantee,
      actions: ['dynamodb:PartiQLUpdate'],
      resourceArns: [this.objectTable.tableArn],
    });
  }

  // creates an `EventPattern` that triggers when an object is created in
  // a given folder in the objects bucket.
  private objectCreatedEventPattern(pathPrefix: string): events.EventPattern {
    return {
      account: [Stack.of(this).account],
      region: [Stack.of(this).region],
      source: ['aws.s3'],
      resources: [this.objectsBucket.bucketArn],
      detailType: ['Object Created'],
      detail: {
        object: {
          key: [{ prefix: pathPrefix }],
        },
      },
    };
  }
}
