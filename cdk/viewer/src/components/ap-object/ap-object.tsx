import { component$ } from '@builder.io/qwik';

import Note from '~/components/note/note';
import type { APObject } from '~/types/objects';
import styles from './ap-object.module.css';

interface APObjectProps {
  object: APObject;
}

export default component$(({ object }: APObjectProps) => {
  return (
    <div class={styles.container}>
      {object.type === 'Note' ? <Note note={object} /> :
      <p>{object.type}</p>}
    </div>
  );
});
