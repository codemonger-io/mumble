import {
  QueryCommand,
  type QueryCommandInput,
  type QueryCommandOutput,
} from '@aws-sdk/lib-dynamodb';
import { component$ } from '@builder.io/qwik';
import { routeLoader$ } from '@builder.io/qwik-city';
// import DOMPurify from 'isomorphic-dompurify';

import type { Activity, ActivityMetadata } from '~/types/activity';
import {
  AsyncIteratorWrapper,
  type FnAsyncIterator,
} from '~/utils/fn-async-iterator';
import { loadActivity } from '~/utils/activities';
import { getDynamoDbClient } from '~/utils/dynamodb';
import { format_yyyy_mm } from '~/utils/datetime';
import { isFailReturn } from '~/utils/fail-return';
import { useUserInfo } from '../layout';

// fetches the recent user activities from the database
export const useUserActivities = routeLoader$(async requestEvent => {
  console.log('OBJECT_TABLE_NAME', process.env.OBJECT_TABLE_NAME)
  const { id } = requestEvent.params;
  // uses the user info to know the last activity date
  const userInfo = await requestEvent.resolveValue(useUserInfo);
  if (isFailReturn(userInfo)) {
    return userInfo;
  }
  const createdAt = new Date(userInfo.createdAt);
  const lastActivityAt = new Date(userInfo.lastActivityAt);
  // fetches up to 20 activities
  const activities = fetchActivities(id, lastActivityAt, createdAt);
  try {
    return await activities.take(20).collect();
  } finally {
    activities.return();
  }
});

// fetches latest activities of a given user from the database.
function fetchActivities(
  username: string,
  before: Date,
  after: Date,
): FnAsyncIterator<Activity> {
  return AsyncIteratorWrapper
    .from(fetchMetaActivities(username, before, after), { lookAhead: 10 })
    .map(loadActivity);
}

// fetches latest meta activities of a given user from the database.
async function* fetchMetaActivities(
  username: string,
  before: Date,
  after: Date,
): AsyncGenerator<ActivityMetadata> {
  const client = getDynamoDbClient();
  let year = before.getUTCFullYear();
  let month = before.getUTCMonth() + 1; // 0-11 → 1-12
  let currentYM = format_yyyy_mm(year, month);
  const oldestYM = format_yyyy_mm(
    after.getUTCFullYear(),
    after.getUTCMonth() + 1,
  );
  while (currentYM >= oldestYM) {
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
    month--;
    if (month === 0) {
      month = 12;
      year--;
    }
    currentYM = format_yyyy_mm(year, month);
  }
}

export default component$(() => {
  const activities = useUserActivities();
  if (isFailReturn(activities.value)) {
    return <p>{activities.value.errorMessage}</p>;
  }

  return (
    <>
      <h2>Recent activities</h2>
      {activities.value.map(activity => (
        <div key={activity.id}>
          <p dangerouslySetInnerHTML={activity.object?.content ?? ""}>
          </p>
        </div>
      ))}
    </>
  );
});
