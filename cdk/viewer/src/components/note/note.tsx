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
    <article class={styles.container}>
      <div
        class={styles.markdown}
        dangerouslySetInnerHTML={safeContent.value}
      ></div>
      {note.attachment && (
        <div class={styles.attachments}>
          <p class={styles['attachments-summary']}>
            {note.attachment.length}
            {note.attachment.length > 1 ? 'attachments' : 'attachment'}
          </p>
          {note.attachment.filter(a => a.type === 'Image').map(attachment => (
            <article class={styles['image-container']}>
              <img
                key={attachment.url}
                src={attachment.url}
              ></img>
            </article>
          ))}
        </div>
      )}
    </article>
  );
});
