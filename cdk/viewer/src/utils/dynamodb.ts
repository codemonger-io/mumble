import { DynamoDBClient } from '@aws-sdk/client-dynamodb';
import { DynamoDBDocumentClient } from '@aws-sdk/lib-dynamodb';

let _dynamodb: DynamoDBDocumentClient | undefined;

/**
 * Obtains the shared DynamoDB client.
 *
 * @remarks
 *
 * Initializes the client if it has not been initialized.
 */
export function getDynamoDbClient(): DynamoDBDocumentClient {
  if (_dynamodb == null) {
    const client = new DynamoDBClient({});
    _dynamodb = DynamoDBDocumentClient.from(client);
  }
  return _dynamodb;
}
