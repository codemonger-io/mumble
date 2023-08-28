import type { APObject, Attachment } from '~/types/objects';

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
