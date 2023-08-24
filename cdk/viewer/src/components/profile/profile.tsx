import { component$ } from '@builder.io/qwik';
import { SiMastodon } from '@qwikest/icons/simpleicons';

import CopyableText from '~/components/copyable-text/copyable-text';
import type { UserInfo } from '~/types/user-info';
import styles from './profile.module.css';

interface ProfileProps {
  user: UserInfo;
  domainName: string;
}

export default component$(({ user, domainName }: ProfileProps) => {
  return (
    <article class={styles.container}>
      <h1 class={styles.name}>{user.name}</h1>
      <h2 class={styles['preferred-name']}>@{user.preferredUsername}</h2>
      <p>{user.summary}</p>
      <p>Followers: {user.followerCount}</p>
      <p>Following: {user.followingCount}</p>
      <p>
        🔍 Search
        <CopyableText text={`@${user.preferredUsername}@${domainName}`} />
        on your <SiMastodon class={styles.mastodon} /> Mastodon client to follow.
      </p>
    </article>
  );
});
