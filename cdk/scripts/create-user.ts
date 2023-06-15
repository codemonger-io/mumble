/**
 * Creates a user.
 *
 * @remarks
 *
 * This script does the following jobs necessary to create a new Mumble user
 * for you:
 * - Create a Cognito user
 * - Generate a key pair for the user
 * - Save the private key in Parameter Store
 * - Create an entry in the user table for the user
 */

import * as crypto from 'crypto';
import * as util from 'util';

import yargs from 'yargs';
import { hideBin } from 'yargs/helpers';
import {
  CloudFormationClient,
  DescribeStacksCommand,
} from '@aws-sdk/client-cloudformation';
import {
  AdminCreateUserCommand,
  CognitoIdentityProviderClient,
} from '@aws-sdk/client-cognito-identity-provider';
import { DynamoDBClient } from '@aws-sdk/client-dynamodb';
import { PutParameterCommand, SSMClient } from '@aws-sdk/client-ssm';
import { DynamoDBDocumentClient, PutCommand } from '@aws-sdk/lib-dynamodb';

import type { DeploymentStage } from '../lib/deployment-stage';
import { DEPLOYMENT_STAGES, isDeploymentStage } from '../lib/deployment-stage';

const promiseGenerateKeyPair = util.promisify(crypto.generateKeyPair);

const STACK_NAME_PREFIX = 'mumble-';

yargs(hideBin(process.argv))
  .command(
    '$0 <username> <email>',
    'Creates a new user',
    yargs => {
      return yargs
        .positional('username', {
          describe: 'username of the user to be created',
          type: 'string',
        })
        .positional('email', {
          describe: 'email of the user to be created',
          type: 'string',
        })
        .options({
          stage: {
            describe: 'deployment stage where to create the user',
            choices: DEPLOYMENT_STAGES,
            default: 'development' as DeploymentStage,
          },
          name: {
            describe: 'full name of the user to be created',
            type: 'string',
            default: '',
          },
          summary: {
            describe: 'summary about the user to be created',
            type: 'string',
            default: '',
          },
          url: {
            describe: 'URL associated with the user to be created',
            type: 'string',
            default: '',
          },
        });
    },
    async ({ username, email, stage, name, summary, url }) => {
      if (username == null) {
        throw new Error('username is required');
      }
      if (email == null) {
        throw new Error('email is required');
      }
      if (!isDeploymentStage(stage)) {
        throw new Error(
          'stage must be one of: ' + DEPLOYMENT_STAGES.join(', '),
        )
      }
      console.log('obtaining stage resources:', stage);
      const resources = await getResources(stage);
      console.log('creating user:', username);
      await createCognitoUser(resources.userPoolId, username, email);
      const keyPair = await generateKeyPair();
      const privateKeyPath = await savePrivateKey(
        resources.privateKeyPathPrefix,
        keyPair.privateKey,
      );
      await createUserEntry(resources.userTableName, {
        username,
        publicKeyPem: keyPair.publicKey,
        privateKeyPath,
        name,
        summary,
        url,
      });
      console.log('done.');
    },
  )
  .help()
  .argv;

/** Resources. */
interface Resources {
  /** User pool ID. */
  readonly userPoolId: string;
  /** Path prefix for a private key in Parameter Store. */
  readonly privateKeyPathPrefix: string;
  /** Name of the user table. */
  readonly userTableName: string;
}

/** Key pair. */
interface KeyPair {
  /** Public key (PEM). */
  readonly publicKey: string;
  /** Private key (PEM). */
  readonly privateKey: string;
}

/** Properties of a user. */
interface UserProps {
  /** Username. */
  readonly username: string;
  /** PEM representation of the public key. */
  readonly publicKeyPem: string;
  /** Path to the private key. */
  readonly privateKeyPath: string;
  /** Full name. */
  readonly name: string;
  /** Summary. */
  readonly summary: string;
  /** URL. */
  readonly url: string;
}

/** Obtains the resources of a given deployment stage. */
async function getResources(stage: DeploymentStage): Promise<Resources> {
  const client = new CloudFormationClient({});
  const res = await client.send(new DescribeStacksCommand({
    StackName: STACK_NAME_PREFIX + stage,
  }));
  const stack = res.Stacks?.[0];
  if (stack == null) {
    throw new Error('stack not found: ' + stage);
  }
  const outputs = stack.Outputs ?? [];
  const outputMap = new Map<string, string>();
  for (const { OutputKey: key, OutputValue: value } of outputs) {
    if (key != null && value != null) {
      outputMap.set(key, value);
    }
  }
  const userPoolId = outputMap.get('UserPoolId');
  if (userPoolId == null) {
    throw new Error('UserPoolId is not in the stack outputs');
  }
  console.log('user pool ID:', userPoolId);
  const privateKeyPathPrefix = outputMap.get('UserPrivateKeyPathPrefix');
  if (privateKeyPathPrefix == null) {
    throw new Error('UserPrivateKeyPathPrefix is not in the stack outputs');
  }
  console.log('private key path prefix:', privateKeyPathPrefix);
  const userTableName = outputMap.get('UserTableName');
  if (userTableName == null) {
    throw new Error('UserTableName is not in the stack outputs');
  }
  console.log('user table name:', userTableName);
  return {
    userPoolId,
    privateKeyPathPrefix,
    userTableName,
  };
}

/** Creates a new Cognito user. */
async function createCognitoUser(
  userPoolId: string,
  username: string,
  email: string,
): Promise<void> {
  console.log('creating Cognito user', username, email);
  const client = new CognitoIdentityProviderClient({});
  const res = await client.send(new AdminCreateUserCommand({
    UserPoolId: userPoolId,
    Username: username,
    UserAttributes: [
      {
        Name: 'email',
        Value: email,
      },
    ],
    DesiredDeliveryMediums: ['EMAIL'],
  }));
  console.log('created Cognito user:', res);
}

/** Generates a key pair. */
async function generateKeyPair(): Promise<KeyPair> {
  console.log('generating key pair');
  const { publicKey, privateKey } = await promiseGenerateKeyPair('rsa', {
    modulusLength: 4096,
    publicKeyEncoding: {
      type: 'spki',
      format: 'pem',
    },
    privateKeyEncoding: {
      type: 'pkcs8',
      format: 'pem',
    },
  });
  console.log('generated key pair:', publicKey);
  return {
    publicKey,
    privateKey,
  };
}

/**
 * Saves a given private key in Parameter Store.
 *
 * @returns
 *
 *   Path to the saved private key in Parameter Store.
 */
async function savePrivateKey(
  pathPrefix: string,
  privateKey: string,
): Promise<string> {
  const uniquePart = crypto.randomUUID();
  const privateKeyPath = `${pathPrefix}${uniquePart}`;
  console.log('saving private key:', privateKeyPath);
  const client = new SSMClient({});
  const res = await client.send(new PutParameterCommand({
    Name: privateKeyPath,
    Type: 'SecureString',
    Value: privateKey,
    Overwrite: false,
  }));
  console.log('saved private key:', res);
  return privateKeyPath;
}

/** Creates a user entry in the user table. */
async function createUserEntry(
  userTableName: string,
  { username, publicKeyPem, privateKeyPath, name, summary, url }: UserProps,
): Promise<void> {
  console.log('creating user entry:', username);
  const timestamp = formatCurrentTime_yyyymmdd_hhmmss_ssssss();
  const client = DynamoDBDocumentClient.from(new DynamoDBClient({}));
  const res = await client.send(new PutCommand({
    TableName: userTableName,
    Item: {
      pk: `user:${username}`,
      sk: 'reserved',
      preferredUsername: username,
      name,
      summary,
      url,
      publicKeyPem,
      privateKeyPath,
      followerCount: 0,
      followingCount: 0,
      createdAt: timestamp,
      updatedAt: timestamp,
      lastActivityAt: timestamp,
    },
  }));
  console.log('created user entry:', res);
}

/** Formats the current time in the form of "YYYY-MM-DDTHH:mm:ss.ssssssZ". */
function formatCurrentTime_yyyymmdd_hhmmss_ssssss(): string {
  const now = new Date();
  const isoString = now.toISOString();
  return isoString.replace('Z', '000Z');
}
