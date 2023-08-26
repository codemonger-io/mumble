/** Common format of a key of an item in a DynamoDB table. */
export interface ItemKey {
  /** Partition key. */
  readonly pk: string;

  /** Sort key. */
  readonly sk: string;
}
