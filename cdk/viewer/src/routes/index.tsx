import { component$ } from "@builder.io/qwik";
import type { DocumentHead } from "@builder.io/qwik-city";
import { SiGithub } from "@qwikest/icons/simpleicons";

import MumbleBrand from "~/assets/mumble-brand.png?jsx";
import styles from "./index.module.css";

export default component$(() => {
  return (
    <div class={styles.container}>
      <MumbleBrand class={styles.brand} alt="Mumble" />
      <p class={styles.links}>
        <a href="https://github.com/codemonger-io/mumble" target="blank"><SiGithub /></a>
      </p>
      <p class={styles.acknowledgements}>
        Powered by <a href="https://qwik.builder.io" target="_blank">Qwik</a>
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
