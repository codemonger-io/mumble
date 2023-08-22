import {
  QueryCommand,
  type QueryCommandInput,
  type QueryCommandOutput,
} from '@aws-sdk/lib-dynamodb';
import { S3Client, GetObjectCommand } from '@aws-sdk/client-s3';

import type { Activity, ActivityMetadata } from '~/types/activity';
import { format_yyyy_mm } from './datetime';
import { getDynamoDbClient } from './dynamodb';
import {
  AsyncIteratorWrapper,
  type FnAsyncIterator,
} from './fn-async-iterator';

/**
 * Fetches activities of a given user in a specified period from the object
 * store.
 */
export function fetchActivities(
  username: string,
  period: { before: Date, after: Date },
): FnAsyncIterator<Activity> {
  return AsyncIteratorWrapper
    .from(fetchMetaActivities(username, period), { lookAhead: 10 })
    .map(loadActivity);
}

/**
 * Fetches meta activities of a given user in a specified period from the
 * database.
 */
export async function* fetchMetaActivities(
  username: string,
  period: { before: Date, after: Date },
): AsyncGenerator<ActivityMetadata> {
  const client = getDynamoDbClient();
  for (const currentYM of monthsIn(period)) {
    const pk = `activity:${username}:${currentYM}`;
    console.log('querying activities:', pk);
    let exclusiveStartKey: QueryCommandInput['ExclusiveStartKey'] | undefined = undefined;
    do {
      const res: QueryCommandOutput = await client.send(new QueryCommand({
        TableName: process.env.OBJECT_TABLE_NAME,
        KeyConditionExpression: 'pk = :pk',
        FilterExpression: 'isPublic = :true AND #type = :create',
        ExpressionAttributeNames: { '#type': 'type' },
        ExpressionAttributeValues: {
          ':pk': pk,
          ':true': true,
          ':create': 'Create',
        },
        ExclusiveStartKey: exclusiveStartKey,
        ScanIndexForward: false, // reverse chrono
      }));
      for (const item of res.Items ?? []) {
        // TODO: verify ActivityMetadata
        yield item as ActivityMetadata;
      }
      exclusiveStartKey = res.LastEvaluatedKey;
    } while (exclusiveStartKey !== undefined);
  }
}

/** Loads an activity from the object store. */
export async function loadActivity(meta: ActivityMetadata): Promise<Activity> {
  console.log('loading activity:', meta.pk, meta.sk);
  const bucketName = process.env.OBJECTS_BUCKET_NAME;
  const skParts = meta.sk.split(':');
  const uniquePart = skParts[skParts.length - 1];
  const key = `outbox/users/${meta.username}/${uniquePart}.json`;
  const client = new S3Client({});
  try {
    const res = await client.send(new GetObjectCommand({
      Bucket: bucketName,
      Key: key,
    }));
    if (res.Body == null) {
      console.error('missing S3 object body', res);
      throw new Error('missing body');
    }
    const data = await res.Body.transformToString();
    // TODO: verify Activity
    return JSON.parse(data);
  } catch (err) {
    console.error('failed to load activity:', err);
    throw err;
  }
}

/**
 * Iterates over months in a given period.
 *
 * @remarks
 *
 * Months are enumerated reverse chronologically.
 *
 * Each item is represented in the "yyyy-mm" format.
 */
function* monthsIn(
  { before, after }: { before: Date, after: Date },
): Generator<string> {
  let year = before.getUTCFullYear();
  let month = before.getUTCMonth() + 1; // 0-11 → 1-12
  let currentYM = format_yyyy_mm(year, month);
  const oldestYM = format_yyyy_mm(
    after.getUTCFullYear(),
    after.getUTCMonth() + 1,
  );
  while (currentYM >= oldestYM) {
    yield currentYM;
    month--;
    if (month === 0) {
      month = 12;
      year--;
    }
    currentYM = format_yyyy_mm(year, month);
  }
}
