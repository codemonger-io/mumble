/** Object in ActivityPub. */
export interface APObject {
  /** ID of the object. */
  id: string;

  /** Type of the object. */
  type: string;

  /** Optional MIME type of the object. */
  mediaType?: string;

  /** Optional content of the object. */
  content?: string;

  /** Optional attachments. */
  attachment?: Attachment[];
}

/**
 * Attachment in ActivityPub.
 *
 * @remarks
 *
 * There is no `Attachment` type in ActivityPub, though, this interface shows
 * expected fields.
 */
export interface Attachment {
  /** Type of the object. */
  type: string;

  /** URL of the attachment. */
  url: string;
}
