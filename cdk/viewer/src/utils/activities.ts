import { S3Client, GetObjectCommand } from '@aws-sdk/client-s3';
import type { Activity, ActivityMetadata } from '~/types/activity';

/** Loads an activity from the object store. */
export async function loadActivity(meta: ActivityMetadata): Promise<Activity> {
  console.log('loading activity:', meta.pk, meta.sk);
  const bucketName = process.env.OBJECTS_BUCKET_NAME;
  const skParts = meta.sk.split(':');
  const uniquePart = skParts[skParts.length - 1];
  const key = `outbox/users/${meta.username}/${uniquePart}.json`;
  const client = new S3Client({});
  try {
    const res = await client.send(new GetObjectCommand({
      Bucket: bucketName,
      Key: key,
    }));
    if (res.Body == null) {
      console.error('missing S3 object body', res);
      throw new Error('missing body');
    }
    const data = await res.Body.transformToString();
    // TODO: verify Activity
    return JSON.parse(data);
  } catch (err) {
    console.error('failed to load activity:', err);
    throw err;
  }
}
