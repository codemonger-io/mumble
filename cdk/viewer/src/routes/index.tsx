import { component$ } from "@builder.io/qwik";
import type { DocumentHead } from "@builder.io/qwik-city";
import { SiGithub } from "@qwikest/icons/simpleicons";

import MumbleBrand from "~/assets/mumble-brand.png?jsx";
import styles from "./index.module.css";

export default component$(() => {
  return (
    <div class={styles.container}>
      <MumbleBrand class={styles.brand} />
      <p class={styles.links}>
        <a href="https://github.com/codemonger-io/mumble"><SiGithub /></a>
      </p>
    </div>
  );
});

export const head: DocumentHead = {
  title: "Welcome to Mumble",
  meta: [
    {
      name: "description",
      content: "Mumble viewer app",
    },
  ],
};
