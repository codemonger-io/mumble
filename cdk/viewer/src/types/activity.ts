import type { ItemKey } from './dynamodb';
import type { APObject } from './objects';

/** Metadata of an activity. */
export interface ActivityMetadata extends ItemKey {
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
