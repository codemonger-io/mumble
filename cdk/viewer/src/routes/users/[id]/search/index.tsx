import { component$ } from '@builder.io/qwik';
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
    console.log('searching for similar mumblings:', embedding);
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
    console.log('resolving mumblings:', results);
    let mumblings;
    try {
      mumblings = await Promise.all(results.map((r) => loadObject(r.id)));
      mumblings = mumblings.map((m) => stripObject(m));
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

export default component$(() => {
  const search = useSearchMumbling();
  if (search.value?.failed) {
    if (search.value.fieldErrors) {
      return <p>{search.value.fieldErrors.terms}</p>
    } else {
      return <p>{search.value.errorMessage}</p>;
    }
  }

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
              value={search.formData?.get('terms')?.toString() ?? ''}
              placeholder="Free-form text to search: keywords, sentences, etc."
              maxlength={1024}
            />
            <button type="submit">Search</button>
          </Form>
        </div>
        <div class={styles.objects}>
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
