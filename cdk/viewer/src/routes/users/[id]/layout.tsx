import { GetCommand } from '@aws-sdk/lib-dynamodb';
import {
  $,
  Slot,
  component$,
  useOnWindow,
  useSignal,
  useTask$,
} from '@builder.io/qwik';
import { isBrowser } from '@builder.io/qwik/build';
import { routeLoader$ } from '@builder.io/qwik-city';

import Profile from '~/components/profile/profile';
import type { UserInfo } from '~/types/user-info';
import { getDynamoDbClient } from '~/utils/dynamodb';
import { isFailReturn } from '~/utils/fail-return';
import { getDomainNameParameter } from '~/utils/parameters';
import styles from './layout.module.css';

// fetches user information from the database
export const useUserInfo = routeLoader$(async requestEvent => {
  const userId = requestEvent.params.id;
  console.log('obtaining user info for:', userId);
  const client = getDynamoDbClient();
  const res = await client.send(new GetCommand({
    TableName: process.env.USER_TABLE_NAME,
    Key: {
      'pk': `user:${userId}`,
      'sk': 'reserved',
    },
  }));
  if (res.Item == null) {
    // no user found
    return requestEvent.fail(404, {
      errorMessage: 'User not found',
    });
  }
  // TODO: verify UserInfo
  return res.Item as UserInfo;
});

// obtains the domain name.
export const useDomainName = routeLoader$(async () => {
  const domainName = await getDomainNameParameter();
  if (domainName != null) {
    return domainName;
  }
  if (process.env.ORIGIN) {
    try {
      return new URL(process.env.ORIGIN).host;
    } catch (err) {
      console.warn('ORIGIN is not a valid URL:', process.env.ORIGIN);
    }
  }
  return 'localhost';
});

export default component$(() => {
  const userInfo = useUserInfo();
  if (isFailReturn(userInfo.value)) {
    return <p>{userInfo.value.errorMessage}</p>
  }

  const domainName = useDomainName();

  // hides the "Move to top" button after 2 seconds,
  // but keeps it visible if the user is hovering over or pressing it.
  const isMoveToTopShown = useSignal(false);
  const isMoveToTopTransient = useSignal(false);
  const isMoveToTopHeld = useSignal(false);
  useTask$(({ track, cleanup }) => {
    track(() => isMoveToTopShown.value);
    if (isBrowser) {
      if (isMoveToTopShown.value) {
        // transient state ensures that `display` is not `none`
        // before the transition runs
        isMoveToTopTransient.value = true;
        window.requestAnimationFrame(() => {
          isMoveToTopTransient.value = false;
        });
        const timeoutId = setTimeout(() => {
          if (isMoveToTopShown.value && !isMoveToTopHeld.value) {
            // transient state ensures that `display` is not `none`
            // while the transition is running
            isMoveToTopTransient.value = true;
            isMoveToTopShown.value = false;
          }
        }, 2000);
        cleanup(() => {
          clearTimeout(timeoutId);
          isMoveToTopShown.value = false;
        });
      }
    }
  });
  useTask$(({ track }) => {
    track(() => isMoveToTopHeld.value);
    if (isBrowser) {
      if (isMoveToTopShown.value && !isMoveToTopHeld.value) {
        isMoveToTopTransient.value = true;
        isMoveToTopShown.value = false;
      }
    }
  });

  // shows the "Move to top" button when the user scrolls up.
  const containerRef = useSignal<Element>();
  const lastScrollY = useSignal(0);
  useOnWindow('scroll', $(() => {
    const containerRect = containerRef.value?.getBoundingClientRect();
    if (containerRect == null) {
      return;
    }
    const scrollDelta = window.scrollY - lastScrollY.value;
    lastScrollY.value = window.scrollY;
    if (scrollDelta < 0) {
      if (window.scrollY > window.innerHeight) {
        isMoveToTopShown.value = true;
      }
    }
  }));

  return (
    <div ref={containerRef} class={styles.container}>
      <nav class={styles.navigation}>
        <div class={styles.level}>
          <header>
            <Profile user={userInfo.value} domainName={domainName.value} />
          </header>
          <main>
            <Slot />
          </main>
        </div>
        <footer class={styles.footer}>
          <p>Powered by <a href="https://qwik.builder.io" target="_blank">Qwik</a></p>
        </footer>
      </nav>
      <button
        class={[
          styles['move-to-top'],
          (isMoveToTopShown.value || isMoveToTopHeld.value) && styles['move-to-top-active'],
          isMoveToTopTransient.value && styles['move-to-top-transient'],
        ]}
        onClick$={() => window.scrollTo({ top: 0, behavior: 'smooth' })}
        onPointerEnter$={() => isMoveToTopHeld.value = true}
        onPointerLeave$={() => isMoveToTopHeld.value = false}
        onPointerDown$={() => isMoveToTopHeld.value = true}
        onPointerUp$={() => isMoveToTopHeld.value = false}
        onTransitionEnd$={() => isMoveToTopTransient.value = false}
      >👆 Move to top</button>
    </div>
  );
});
