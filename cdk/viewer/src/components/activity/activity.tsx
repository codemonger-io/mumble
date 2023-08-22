import { component$ } from '@builder.io/qwik';

import Note from '~/components/note/note';
import type { Activity } from '~/types/activity';
import type { APObject } from '~/types/objects';

interface ActivityProps {
  activity: Activity;
}

export default component$(({ activity }: ActivityProps) => {
  return (
    <div>
      {activity.type === 'Create' ? <Create object={activity.object} /> :
      <p>{activity.type}</p>}
    </div>
  );
});

export const Create = component$(({ object }: { object?: APObject }) => {
  return (
    <>
      {object?.type === 'Note' ? <Note note={object} /> :
      <p>{object?.type}</p>}
    </>
  );
});
