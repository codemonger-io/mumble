import {
  Duration,
  RemovalPolicy,
  aws_iam as iam,
  aws_s3 as s3,
  aws_s3_notifications as notifications,
  aws_sqs as sqs,
} from 'aws-cdk-lib';
import { Construct } from 'constructs';

/** Paht prefix of the inbox. */
export const INBOX_PREFIX = 'inbox/';

/** Properties for `ObjectStore`. */
export interface Props {
  /** Common dead-letter queue for S3 event queues. */
  readonly deadLetterQueue: sqs.IQueue;
}

/** CDK construct that provisions the S3 bucket for objects. */
export class ObjectStore extends Construct {
  /** S3 bucket for objects. */
  readonly objectsBucket: s3.IBucket;
  /** SQS queue that notifies when an object is put in the inbox. */
  readonly inboxQueue: sqs.IQueue;

  constructor(scope: Construct, id: string, props: Props) {
    super(scope, id);

    const { deadLetterQueue } = props;

    this.objectsBucket = new s3.Bucket(this, 'ObjectsBucket', {
      blockPublicAccess: s3.BlockPublicAccess.BLOCK_ALL,
      encryption: s3.BucketEncryption.S3_MANAGED,
      removalPolicy: RemovalPolicy.RETAIN,
    });

    // event queues for the bucket
    // - notifies a new object in the inbox
    this.inboxQueue = new sqs.Queue(this, 'InboxQueue', {
      encryption: sqs.QueueEncryption.SQS_MANAGED,
      deliveryDelay: Duration.seconds(0),
      receiveMessageWaitTime: Duration.seconds(0),
      retentionPeriod: Duration.days(1),
      visibilityTimeout: Duration.minutes(1),
      deadLetterQueue: {
        maxReceiveCount: 15, // TBC: appropriate number?
        queue: deadLetterQueue,
      },
    });
    this.objectsBucket.addEventNotification(
      s3.EventType.OBJECT_CREATED,
      new notifications.SqsDestination(this.inboxQueue),
      {
        prefix: INBOX_PREFIX,
      },
    );
  }

  /** Grants a given principal "Put" access to the inbox. */
  grantPutIntoInbox(grantee: iam.IGrantable): iam.Grant {
    return this.objectsBucket.grantPut(grantee, INBOX_PREFIX + '*');
  }
}
