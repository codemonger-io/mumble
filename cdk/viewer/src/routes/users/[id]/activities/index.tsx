import { component$ } from '@builder.io/qwik';
import { routeLoader$ } from '@builder.io/qwik-city';

import Activity from '~/components/activity/activity';
import { fetchActivities } from '~/utils/activities';
import { isFailReturn } from '~/utils/fail-return';
import { useUserInfo } from '../layout';
import styles from './index.module.css';

// fetches the recent user activities from the database
export const useUserActivities = routeLoader$(async requestEvent => {
  const { id } = requestEvent.params;
  // uses the user info to know the last activity date
  const userInfo = await requestEvent.resolveValue(useUserInfo);
  if (isFailReturn(userInfo)) {
    return userInfo;
  }
  const createdAt = new Date(userInfo.createdAt);
  const lastActivityAt = new Date(userInfo.lastActivityAt);
  // fetches up to 20 activities
  const activities = fetchActivities(id, {
    before: lastActivityAt,
    after: createdAt,
  });
  try {
    return await activities.take(20).collect();
  } finally {
    activities.return();
  }
});

export default component$(() => {
  const activities = useUserActivities();
  if (isFailReturn(activities.value)) {
    return <p>{activities.value.errorMessage}</p>;
  }

  return (
    <section class={styles.container}>
      <h2 class={styles.title}>Recent mumbling</h2>
      <div class={styles.content}>
        {activities.value.map(activity => (
          <Activity key={activity.id} activity={activity} />
        ))}
      </div>
    </section>
  );
});
