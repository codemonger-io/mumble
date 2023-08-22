import { component$ } from '@builder.io/qwik';
import { routeLoader$ } from '@builder.io/qwik-city';

import { fetchActivities } from '~/utils/activities';
import { isFailReturn } from '~/utils/fail-return';
import { useUserInfo } from '../layout';

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