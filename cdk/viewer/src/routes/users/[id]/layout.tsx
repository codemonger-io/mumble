import { GetCommand } from '@aws-sdk/lib-dynamodb';
import { Slot, component$ } from '@builder.io/qwik';
import { routeLoader$ } from '@builder.io/qwik-city';

import type { UserInfo } from '~/types/user-info';
import { getDynamoDbClient } from '~/utils/dynamodb';
import { isFailReturn } from '~/utils/fail-return';

// fetches user information from the database
export const useUserInfo = routeLoader$(async requestEvent => {
  const userId = requestEvent.params.id;
  console.log('obtaining user info for:', userId);
  const client = getDynamoDbClient();
  const res = await client.send(new GetCommand({
    TableName: process.env.USER_TABLE_NAME,
    Key: {
      'pk': `user:${userId}`,
      'sk': 'reserved',
    },
  }));
  if (res.Item == null) {
    // no user found
    return requestEvent.fail(404, {
      errorMessage: 'User not found',
    });
  }
  // TODO: verify UserInfo
  return res.Item as UserInfo;
});

export default component$(() => {
  const userInfo = useUserInfo();
  if (isFailReturn(userInfo.value)) {
    return <p>{userInfo.value.errorMessage}</p>
  }

  return (
    <>
      <header>
        <h1>Hello, {userInfo.value.name} (@{userInfo.value.preferredUsername})</h1>
        <p>{userInfo.value.summary}</p>
        <p>Followers: {userInfo.value.followerCount}</p>
        <p>Following: {userInfo.value.followingCount}</p>
      </header>
      <main>
        <Slot />
      </main>
    </>
  );
});
