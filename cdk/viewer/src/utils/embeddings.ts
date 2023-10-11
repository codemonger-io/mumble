import { getOpenAiApiKeyParameter } from '~/utils/parameters';

const EMBEDDING_ENDPOINT = 'https://api.openai.com/v1/embeddings';
const EMBEDDING_MODEL = 'text-embedding-ada-002';

// OpenAI API key.
//
// You have to configure the environment variable
// `OPENAI_API_KEY_PARAMETER_PATH` that specifies the path to the parameter that
// stores the OpenAI API key for embedding calculation in the Parameter Store on
// AWS Systems Manager.
//
// This variable caches the API key.
let openaiApiKey: string | null = null;

/**
 * Creates an embedding vector of a given text.
 *
 * @remarks
 *
 * You have to configure the environment variable
 * `OPENAI_API_KEY_PARAMETER_PATH`.
 */
export async function createEmbedding(text: string): Promise<[number]> {
  if (openaiApiKey == null) {
    openaiApiKey = await getOpenAiApiKeyParameter();
  }
  const res = await fetch(EMBEDDING_ENDPOINT, {
    method: 'POST',
    headers: {
      Authorization: `Bearer ${openaiApiKey}`,
      'Content-Type': 'application/json',
    },
    body: JSON.stringify({
      model: EMBEDDING_MODEL,
      input: text,
      user: 'mumble',
    }),
  });
  if (res.status !== 200) {
    throw new Error(
      `embedding request failed with ${res.status}: ${await res.text()}`,
    );
  }
  const result = await res.json();
  if (!Array.isArray(result.data)) {
    throw new Error(
      'unexpected response from OpenAI API: data is not an array',
    );
  }
  if (result.data.length === 0) {
    throw new Error('unexpected response from OpenAI API: data is empty');
  }
  if (result.data.length > 1) {
    console.warn(
      'unexpected response from OpenAI API: more than one embeddings',
    );
  }
  const embedding = result.data[0];
  if (!Array.isArray(embedding.embedding)) {
    throw new Error(
      'unexpected response from OpenAI API: embedding is not array',
    );
  }
  return embedding.embedding;
}
