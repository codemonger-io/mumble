import type { RequestEvent } from '@builder.io/qwik-city';

// redirects to ./activities
export const onGet = async ({ redirect }: RequestEvent) => {
  throw redirect(303, './activities');
};
