import { component$ } from '@builder.io/qwik';
import { SiMastodon } from '@qwikest/icons/simpleicons';

import MumbleLogo from '~/assets/mumble-logo.svg?jsx';
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
      <article class={styles['profile-image']}>
        <MumbleLogo />
      </article>
      <h1 class={styles.name}>{user.name}</h1>
      <h2 class={styles['preferred-name']}>@{user.preferredUsername}</h2>
      <article>
        <p>{user.summary}</p>
      </article>
      {user.url && (
        <article>
          🔗 <a href={user.url} target="_blank">{user.url}</a>
        </article>
      )}
      <article>
        <p>Followers: {user.followerCount}</p>
        <p>Following: {user.followingCount}</p>
      </article>
      <article>
        <p>
          🔍 Search
          <CopyableText text={`@${user.preferredUsername}@${domainName}`} />
          on your <a href="https://joinmastodon.org" target="_blank"><SiMastodon class={styles.mastodon} /> Mastodon</a> client to follow.
        </p>
      </article>
    </article>
  );
});
