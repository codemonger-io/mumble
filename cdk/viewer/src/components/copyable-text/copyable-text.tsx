import { component$, useSignal, useTask$ } from '@builder.io/qwik';
import { LuCopy } from '@qwikest/icons/lucide';

import styles from './copyable-text.module.css';

interface CopyableTextProps {
  text: string;
}

export default component$(({ text }: CopyableTextProps) => {
  const isHovered = useSignal(false);
  const copyResult = useSignal(null as null | 'success' | 'error');
  const copyResultMessage = useSignal('');

  useTask$(async ({ track, cleanup }) => {
    track(() => copyResult.value);
    if (copyResult.value == null) {
      return;
    }
    const timeoutId = setTimeout(() => {
      copyResult.value = null;
    }, 1000);
    cleanup(() => {
      clearTimeout(timeoutId);
      copyResult.value = null;
    });
  });

  return (
    <span
      class={[styles.container, { [styles.hovered]: isHovered.value }]}
      onPointerEnter$={() => isHovered.value = true}
      onPointerLeave$={() => isHovered.value = false}
    >
      <span class={styles.clipped}>
        <span class={styles.text}>{text}</span>
      </span>
      <button
        class={styles['copy-button']}
        onClick$={async () => {
          try {
            await navigator.clipboard.writeText(text);
            copyResultMessage.value = 'Copied to clipboard';
            copyResult.value = 'success';
          } catch (err) {
            console.error(err);
            copyResultMessage.value = 'Clipboard unavailable';
            copyResult.value = 'error';
          }
        }}
      ><LuCopy /></button>
      <span
        class={[
          styles['copy-notice'],
          copyResult.value && styles[copyResult.value],
        ]}
      >{copyResultMessage.value}</span>
    </span>
  );
});
