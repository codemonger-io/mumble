import { component$ } from '@builder.io/qwik';

import styles from './activity-loading.module.css';

interface ActivityLoadingProps {
  message: string;
}

export default component$(({ message }: ActivityLoadingProps) => {
  return (
    <div class={styles.container}>
      <p>{message}</p>
    </div>
  );
});
