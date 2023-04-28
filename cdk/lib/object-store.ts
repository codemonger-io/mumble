import {
  Duration,
  RemovalPolicy,
  Stack,
  aws_events as events,
  aws_iam as iam,
  aws_s3 as s3,
} from 'aws-cdk-lib';
import { Construct } from 'constructs';

/** Paht prefix of the inbox. */
export const INBOX_PREFIX = 'inbox/';
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
 * #### Objects
 *
 * The objects (`objects`) folder stores non-activity objects.
 *
 * Every user `{username}` has a dedicated folder in the objects folder:
 * `objects/users/{username}`
 *
 * I am planning to further split folders in user's folder:
 * - `objects/users/{username}/posts`: for posts
 * - `objects/users/{username}/media`: for media files: e.g., images, videos
 */
export class ObjectStore extends Construct {
  /** S3 bucket for objects. */
  readonly objectsBucket: s3.IBucket;
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
   * EventBridge Rule that triggers when a new object is created in the staging
   * outbox folder in the S3 bucket.
   *
   * @remarks
   *
   * Please add a target to handle events.
   */
  readonly stagingOutboxObjectCreatedRule: events.Rule;

  constructor(scope: Construct, id: string) {
    super(scope, id);

    this.objectsBucket = new s3.Bucket(this, 'ObjectsBucket', {
      blockPublicAccess: s3.BlockPublicAccess.BLOCK_ALL,
      encryption: s3.BucketEncryption.S3_MANAGED,
      eventBridgeEnabled: true,
      removalPolicy: RemovalPolicy.RETAIN,
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
        eventPattern: {
          account: [Stack.of(this).account],
          region: [Stack.of(this).region],
          source: ['aws.s3'],
          resources: [this.objectsBucket.bucketArn],
          detailType: ['Object Created'],
          detail: {
            object: {
              key: [{ prefix: INBOX_PREFIX }],
            },
          },
        },
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
        eventPattern: {
          account: [Stack.of(this).account],
          region: [Stack.of(this).region],
          source: ['aws.s3'],
          resources: [this.objectsBucket.bucketArn],
          detailType: ['Object Created'],
          detail: {
            object: {
              key: [{ prefix: STAGING_OUTBOX_PREFIX }],
            },
          },
        },
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

  /** Grants a given principal "Get" access from the staging outbox. */
  grantGetFromStagingOutbox(grantee: iam.IGrantable): iam.Grant {
    return this.objectsBucket.grantRead(grantee, STAGING_OUTBOX_PREFIX + '*');
  }
}
