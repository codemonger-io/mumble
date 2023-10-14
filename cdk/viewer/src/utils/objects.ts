import { GetObjectCommand, S3Client } from '@aws-sdk/client-s3';

import type { APObject, Attachment } from '~/types/objects';

/**
 * Loads an object from the object store.
 *
 * @remarks
 *
 * You have to specify the name of the S3 bucket that manages the objects to
 * the environment variable `OBJECTS_BUCKET_NAME`.
 *
 * @param id
 *
 *   ID (URL) of the object to load.
 */
export async function loadObject(id: string): Promise<APObject> {
  console.log('loading object', id);
  const bucketName = process.env.OBJECTS_BUCKET_NAME;
  const url = new URL(id);
  const key = `objects${url.pathname}.json`;
  const client = new S3Client({});
  try {
    const res = await client.send(new GetObjectCommand({
      Bucket: bucketName,
      Key: key,
    }));
    if (res.Body == null) {
      console.error('mssing S3 objrect body', res);
      throw new Error('missing body');
    }
    const data = await res.Body.transformToString();
    // TODO: verify Object
    return JSON.parse(data);
  } catch (err) {
    console.error('failed to load object:', err);
    throw err;
  }
}

/** Drops unnecessary fields from a given object. */
export function stripObject(obj: APObject): APObject {
  return {
    id: obj.id,
    type: obj.type,
    ...(obj.mediaType != null ? { mediaType: obj.mediaType } : {}),
    ...(obj.content != null ? { content: obj.content } : {}),
    ...(obj.attachment != null
      ? { attachment: obj.attachment.map(stripAttachment) }
      : {}),
    ...(obj.published != null ? { published: obj.published } : {}),
  };
}

/** Drops unnecessary fields from a given attachment. */
export function stripAttachment(attachment: Attachment): Attachment {
  return {
    type: attachment.type,
    url: attachment.url,
  };
}
