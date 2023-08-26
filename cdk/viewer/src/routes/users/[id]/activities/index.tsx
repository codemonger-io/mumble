import { $, component$, useOnWindow, useSignal } from '@builder.io/qwik';
import { routeLoader$, server$ } from '@builder.io/qwik-city';

import Activity from '~/components/activity/activity';
import ActivityLoading from '~/components/activity-loading/activity-loading';
import type { ItemKey } from '~/types/dynamodb';
import type { UserInfo } from '~/types/user-info';
import { type ActivityEntry, fetchActivities } from '~/utils/activities';
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
  // fetches up to 20 latest activities
  const activities = fetchActivities(id, {
    beforeDate: new Date(userInfo.lastActivityAt),
    afterDate: new Date(userInfo.createdAt),
  });
  try {
    return await activities.take(20).collect();
  } finally {
    activities.return();
  }
});

const fetchEarlierActivities = server$(async (
  userInfo: UserInfo,
  beforeKey: ItemKey,
) => {
  const activities = fetchActivities(userInfo.preferredUsername, {
    beforeKey,
    afterDate: new Date(userInfo.createdAt),
  });
  // fetches up to 10 earlier activities
  try {
    return await activities.take(10).collect();
  } finally {
    activities.return();
  }
});

export default component$(() => {
  const userInfo = useUserInfo();

  const activities = useUserActivities();
  if (isFailReturn(activities.value)) {
    return <p>{activities.value.errorMessage}</p>;
  }
  const earlierActivities = useSignal([] as ActivityEntry[]);
  const noMoreEarlierActivities = useSignal(false);
  // TODO: compute merged activities

  const isLoading = useSignal(false);

  const containerRef = useSignal<Element>();
  const lastScrollY = useSignal(0);

  useOnWindow('scroll', $(async event => {
    if (isFailReturn(userInfo.value) || isFailReturn(activities.value)) {
      return;
    }
    if (isLoading.value) {
      return;
    }
    const oldScrollY = lastScrollY.value;
    lastScrollY.value = window.scrollY;
    const containerRect = containerRef.value?.getBoundingClientRect();
    if (containerRect != null) {
      const viewportBottom = window.scrollY + window.innerHeight;
      if (
        !noMoreEarlierActivities.value
        && oldScrollY < window.scrollY
        && containerRect.height - viewportBottom < window.innerHeight
      ) {
        // loads new data
        try {
          isLoading.value = true;
          let beforeKey: ItemKey;
          if (earlierActivities.value.length > 0) {
            beforeKey = earlierActivities.value[earlierActivities.value.length - 1]._key;
          } else {
            beforeKey = activities.value[activities.value.length - 1]._key;
          }
          const moreActivities = await fetchEarlierActivities(
            userInfo.value,
            beforeKey,
          );
          if (moreActivities.length === 0) {
            noMoreEarlierActivities.value = true;
          } else {
            earlierActivities.value =
              earlierActivities.value.concat(moreActivities);
          }
        } catch (err) {
          console.error(err);
        } finally {
          isLoading.value = false;
        }
      } else {
        // TODO: show move to top button
      }
    }
  }));

  return (
    <section ref={containerRef} class={styles.container}>
      <h2 class={styles.title}>Recent mumbling</h2>
      <div class={styles.content}>
        {activities.value.map(activity => (
          <Activity key={activity.id} activity={activity} />
        ))}
        {earlierActivities.value.map(activity => (
          <Activity key={activity.id} activity={activity} />
        ))}
        {isLoading.value && (
          <ActivityLoading message="Loading earlier activities..." />
        )}
      </div>
    </section>
  );
});
