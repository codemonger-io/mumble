import * as util from 'node:util';
import { InvokeCommand, LambdaClient } from '@aws-sdk/client-lambda';

// Shared Lambda client.
let lambda: LambdaClient | null = null;

/** Mumbling in similarity search results. */
export interface SimilarMumbling {
  /** ID (URL) of the mumbling fragment. */
  id: string;
  /** Approximate squared distance. */
  distance: number;
}

/**
 * Searches embeddings similar to a given query.
 *
 * @remarks
 *
 * You have to specify the name of the Lambda function that performs actual
 * search to the environment variable `SEARCH_SIMILAR_MUMBLINGS_FUNCTION_NAME`.
 */
export async function searchSimilarMumblings(
  embedding: [number],
): Promise<[SimilarMumbling]> {
  if (process.env.SEARCH_SIMILAR_MUMBLINGS_FUNCTION_NAME == null) {
    throw new Error('SEARCH_SIMILAR_MUMBLINGS_FUNCTION_NAME is not set');
  }
  if (lambda == null) {
    lambda = new LambdaClient({});
  }
  const res = await lambda.send(new InvokeCommand({
    FunctionName: process.env.SEARCH_SIMILAR_MUMBLINGS_FUNCTION_NAME,
    InvocationType: 'RequestResponse',
    Payload: JSON.stringify(embedding),
  }));
  if (res.StatusCode !== 200){
    throw new Error(`similarity search function failed with ${res.StatusCode}`);
  }
  if (res.Payload == null) {
    throw new Error('similarity search function returned nothing');
  }
  const data = new util.TextDecoder().decode(res.Payload);
  const results = JSON.parse(data);
  if (!Array.isArray(results)) {
    throw new Error('similarity search function returned non-array');
  }
  // TODO: verify results
  return results as [SimilarMumbling];
}
