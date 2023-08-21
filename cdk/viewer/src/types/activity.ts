import type { APObject } from './objects';

/** Metadata of an activity. */
export interface ActivityMetadata {
  /** Partition key of the activity. */
  pk: string;

  /** Sort key of the activity. */
  sk: string;

  /** ID of the activity. */
  id: string;

  /** Type of the activity. */
  type: string;

  /** Name of the user who performed the activity. */
  username: string;
}

/** Activity. */
export interface Activity {
  /** ID of the activity. */
  id: string;

  /** Type of the activity. */
  type: string;

  /** Optional object of the activity. */
  object?: APObject;
}
