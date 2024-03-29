import { QueryCommand } from '@aws-sdk/lib-dynamodb';
import { S3Client, GetObjectCommand } from '@aws-sdk/client-s3';

import type { Activity, ActivityMetadata } from '~/types/activity';
import type { ItemKey } from '~/types/dynamodb';
import { format_yyyy_mm } from './datetime';
import { getDynamoDbClient } from './dynamodb';
import {
  AsyncIteratorWrapper,
  type FnAsyncIterator,
} from './fn-async-iterator';
import { stripObject } from './objects';

/** Activity with the database key. */
export type ActivityEntry = Activity & {
  /** Key in the database. */
  readonly _key: ItemKey,
}

/** Options for {@link fetchActivities}. */
export type FetchActivitiesOptions =
  | FetchBeforeDateOptions
  | FetchBeforeKeyOptions;

/** {@link FetchActivitiesOptions} to fetch activities before a given date. */
export interface FetchBeforeDateOptions {
  /** Fetches activities before this date (exclusive). */
  readonly beforeDate: Date;

  /** Fetches activities after this date (exclusive). */
  readonly afterDate: Date;

  readonly beforeKey?: undefined;
}

/** {@link FetchActivitiesOptions} to fetch activities before a given key. */
export interface FetchBeforeKeyOptions {
  /** Fetches activities before this key (exclusive). */
  readonly beforeKey: ItemKey;

  /** Fetches activities after this date (exclusive). */
  readonly afterDate: Date;

  readonly beforeDate?: undefined;
}

/** Fetches activities of a given user from the object store. */
export function fetchActivities(
  username: string,
  options: FetchActivitiesOptions,
): FnAsyncIterator<ActivityEntry> {
  return AsyncIteratorWrapper
    .from(fetchMetaActivities(username, options), { lookAhead: 10 })
    .map(loadActivity)
    .map(async a => stripActivity(a));
}

/**
 * Fetches meta activities of a given user in a specified period from the
 * database.
 */
export async function* fetchMetaActivities(
  username: string,
  options: FetchActivitiesOptions,
): AsyncGenerator<ActivityMetadata> {
  let period: { before: Date, after: Date };
  let exclusiveStartKey: Record<string, any> | undefined = undefined;
  if (options.beforeKey) {
    exclusiveStartKey = options.beforeKey;
    period = {
      before: keyToDate(options.beforeKey),
      after: options.afterDate,
    };
  } else if (options.beforeDate) { // eslint-disable-line @typescript-eslint/no-unnecessary-condition
    period = {
      before: options.beforeDate,
      after: options.afterDate,
    };
  } else {
    // exhaustive check
    const invalid: never = options;
    throw new Error(`invalid options: ${invalid}`);
  }
  const client = getDynamoDbClient();
  for (const currentYM of monthsIn(period)) {
    const pk = `activity:${username}:${currentYM}`;
    console.log('querying activities:', pk);
    do {
      const res = await client.send(new QueryCommand({
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
export async function loadActivity(
  meta: ActivityMetadata,
): Promise<ActivityEntry> {
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
    const activity = JSON.parse(data);
    return {
      ...activity,
      _key: {
        pk: meta.pk,
        sk: meta.sk,
      },
    };
  } catch (err) {
    console.error('failed to load activity:', err);
    throw err;
  }
}

/** Drops unnecessary fields from a given activity. */
export function stripActivity(activity: ActivityEntry): ActivityEntry {
  return {
    _key: activity._key,
    id: activity.id,
    type: activity.type,
    ...(activity.object ? { object: stripObject(activity.object) } : {}),
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

/** Converts a DynamoDB item key into a date. */
function keyToDate(key: ItemKey): Date {
  // pk: activity:<username>:<yyyy-mm>
  // sk: <ddTHH:MM:ss.SSSSSS>:<unique-part>
  const [, , yyyy_mm] = key.pk.split(':');
  const [dd_t_hh, mm, ss_ssssss] = key.sk.split(':');
  const dateStr = `${yyyy_mm}-${dd_t_hh}:${mm}:${ss_ssssss}Z`;
  return new Date(dateStr);
}
