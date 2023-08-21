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
}
