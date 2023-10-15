import { component$, useSignal, useTask$ } from '@builder.io/qwik';
import { Form, routeAction$, z, zod$ } from '@builder.io/qwik-city';

import ActivityLoading from '~/components/activity-loading/activity-loading';
import APObject from '~/components/ap-object/ap-object';
import { createEmbedding } from '~/utils/embeddings';
import { loadObject, stripObject } from '~/utils/objects';
import { type SimilarMumbling, searchSimilarMumblings } from '~/utils/search';
import styles from './index.module.css';

export const useSearchMumbling = routeAction$(
  async (query, requestEvent) => {
    console.log('creating embedding vector');
    let embedding;
    try {
      embedding = await createEmbedding(query.terms);
    } catch (err) {
      console.error(err);
      return requestEvent.fail(500, {
        errorMessage: 'failed to create embedding vector',
      });
    }
    let results;
    try {
      results = await searchSimilarMumblings(embedding);
      // leaves only unique mumblings
      results = results.reduce(
        (results, result) => {
          if (results.find((r) => r.id === result.id) == null) {
            results.push(result);
          }
          return results;
        },
        [] as SimilarMumbling[],
      );
    } catch (err) {
      console.error(err);
      return requestEvent.fail(500, {
        errorMessage: 'failed to search for similar mumblings',
      });
    }
    let mumblings;
    try {
      mumblings = await Promise.all(results.map(async (r) => {
        try {
          return await loadObject(r.id);
        } catch (err) {
          // some objects may not be resolved in the development environment
          return null;
        }
      }));
      mumblings = mumblings
        .filter((m) => m != null)
        .map((m) => stripObject(m!));
    } catch (err) {
      console.error(err);
      return requestEvent.fail(500, {
        errorMessage: 'failed to resolve mumblings',
      });
    }
    return {
      success: true,
      mumblings,
    };
  },
  zod$({
    terms: z.string(),
  }),
);

const MAX_TERMS_LENGTH = 1024;
// Debouncing before triggering search.
const DEBOUNCING_IN_MS = 800;

export default component$(() => {
  const search = useSearchMumbling();
  if (search.value?.failed) {
    if (search.value.fieldErrors) {
      return <p>{search.value.fieldErrors.terms}</p>
    } else {
      return <p>{search.value.errorMessage}</p>;
    }
  }

  const terms = useSignal(search.formData?.get('terms')?.toString() ?? '');
  useTask$(({ track, cleanup }) => {
    track(() => terms.value);
    const debounced = setTimeout(() => {
      if (terms.value.length > 0) {
        search.submit({ terms: terms.value });
      }
    }, DEBOUNCING_IN_MS);
    cleanup(() => clearTimeout(debounced));
  });

  return (
    <section class={styles.container}>
      <h2 class={styles.title}>
        💭 Search mumblings
      </h2>
      <div class={styles.content}>
        <div class={styles.form}>
          <p>
            Type any text in the following form, and we will find similar mumblings.
          </p>
          <Form action={search}>
            <textarea
              name="terms"
              bind:value={terms}
              placeholder="Free-form text to search: keywords, questions, etc."
              maxLength={MAX_TERMS_LENGTH}
            />
          </Form>
        </div>
        <div class={styles.objects}>
          <h3 class={styles.title}>Similar mumblings</h3>
          {search.isRunning
            ? <ActivityLoading message="Searching..." />
            : search.value?.success && search.value.mumblings?.map((m) => (
              <APObject key={m.id} object={m} />
            ))
          }
        </div>
      </div>
    </section>
  );
});
