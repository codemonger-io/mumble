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

/** CDK construct that provisions the S3 bucket for objects. */
export class ObjectStore extends Construct {
  /** S3 bucket for objects. */
  readonly objectsBucket: s3.IBucket;
  /**
   * EventBridge Rule that triggers when a new object is created in the inbox
   * folder in the S3 bucekt.
   *
   * @remarks
   *
   * Add a target to handle events.
   */
  readonly inboxObjectCreatedRule: events.Rule;

  constructor(scope: Construct, id: string) {
    super(scope, id);

    this.objectsBucket = new s3.Bucket(this, 'ObjectsBucket', {
      blockPublicAccess: s3.BlockPublicAccess.BLOCK_ALL,
      encryption: s3.BucketEncryption.S3_MANAGED,
      eventBridgeEnabled: true,
      removalPolicy: RemovalPolicy.RETAIN,
    });

    // S3 notification events should be sent to the default event bus?
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
  }

  /** Grants a given principal "Put" access to the inbox. */
  grantPutIntoInbox(grantee: iam.IGrantable): iam.Grant {
    return this.objectsBucket.grantPut(grantee, INBOX_PREFIX + '*');
  }
}
