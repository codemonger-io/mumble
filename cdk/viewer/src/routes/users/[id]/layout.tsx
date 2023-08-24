import { GetCommand } from '@aws-sdk/lib-dynamodb';
import { Slot, component$ } from '@builder.io/qwik';
import { routeLoader$ } from '@builder.io/qwik-city';

import Profile from '~/components/profile/profile';
import type { UserInfo } from '~/types/user-info';
import { getDynamoDbClient } from '~/utils/dynamodb';
import { isFailReturn } from '~/utils/fail-return';
import { getDomainNameParameter } from '~/utils/parameters';
import styles from './layout.module.css';

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

// obtains the domain name.
export const useDomainName = routeLoader$(async () => {
  const domainName = await getDomainNameParameter();
  if (domainName != null) {
    return domainName;
  }
  if (process.env.ORIGIN) {
    try {
      return new URL(process.env.ORIGIN).host;
    } catch (err) {
      console.warn('ORIGIN is not a valid URL:', process.env.ORIGIN);
    }
  }
  return 'localhost';
});

export default component$(() => {
  const userInfo = useUserInfo();
  if (isFailReturn(userInfo.value)) {
    return <p>{userInfo.value.errorMessage}</p>
  }

  const domainName = useDomainName();

  return (
    <div class={styles.container}>
      <nav class={styles.navigation}>
        <header>
          <Profile user={userInfo.value} domainName={domainName.value} />
        </header>
        <main>
          <Slot />
        </main>
      </nav>
    </div>
  );
});
