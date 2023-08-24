import { component$, useSignal, useVisibleTask$ } from '@builder.io/qwik';
import DOMPurify from 'dompurify';

import type { APObject } from '~/types/objects';
import styles from './note.module.css';

interface NoteProps {
  note: APObject;
}

export default component$<NoteProps>(({ note }: NoteProps) => {
  const safeContent = useSignal('loading content...');
  useVisibleTask$(({ track }) => {
    // DOMPurify won't work on the server
    track(() => note.content);
    safeContent.value = DOMPurify.sanitize(note.content ?? '');
  });

  return (
    <div class={styles.container} dangerouslySetInnerHTML={safeContent.value}>
    </div>
  );
});
