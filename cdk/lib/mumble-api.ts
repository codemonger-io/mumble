import * as path from 'path';
import {
  Duration,
  aws_apigateway as apigateway,
  aws_cloudfront as cloudfront,
  aws_cloudfront_origins as origins,
  aws_lambda as lambda,
} from 'aws-cdk-lib';
import { Construct } from 'constructs';
import { PythonFunction } from '@aws-cdk/aws-lambda-python-alpha';

import { BundledCode, FunctionProps } from 'cdk-cloudfront-function-bundle';
import { RestApiWithSpec } from 'cdk-rest-api-with-spec';
import {
  type MappingTemplateItem,
  composeMappingTemplate,
  ifThen,
  ifThenElse,
} from 'mapping-template-compose';

import type { DeploymentStage } from './deployment-stage';
import type { LambdaDependencies } from './lambda-dependencies';
import type { ObjectStore } from './object-store';
import type { SystemParameters } from './system-parameters';
import type { UserTable } from './user-table';

export interface Props {
  /** Deployment stage. */
  readonly deploymentStage: DeploymentStage;
  /** System parameters. */
  readonly systemParameters: SystemParameters;
  /** Lambda dependencies. */
  readonly lambdaDependencies: LambdaDependencies;
  /** User table. */
  readonly userTable: UserTable;
  /** Object store. */
  readonly objectStore: ObjectStore;
}

/**
 * CDK construct that provisions the Mumble endpoints API.
 *
 * @remarks
 *
 * The Mumble API will comply to the ActivityPub protocol.
 */
export class MumbleApi extends Construct {
  /** REST API that serves as the Mumble endpoints API. */
  readonly api: RestApiWithSpec;
  /** CloudFront distribution of the Mumble endpoints API. */
  readonly distribution: cloudfront.IDistribution;

  constructor(scope: Construct, id: string, props: Props) {
    super(scope, id);

    const {
      deploymentStage,
      lambdaDependencies,
      objectStore,
      systemParameters,
      userTable,
    } = props;
    const { libActivityPub, libCommons, libMumble } = lambdaDependencies;

    // Lambda functions
    // - responds to a WebFinger request
    const webFingerLambda = new PythonFunction(this, 'WebFingerLambda', {
      description: 'Responds to a WebFinger request',
      runtime: lambda.Runtime.PYTHON_3_8,
      architecture: lambda.Architecture.ARM_64,
      entry: path.join('lambda', 'web_finger'),
      index: 'index.py',
      handler: 'lambda_handler',
      layers: [libActivityPub, libCommons, libMumble],
      memorySize: 128,
      timeout: Duration.seconds(5),
      // TODO: specify DOMAIN_NAME in production
    });
    // - describes a given user (actor)
    const describeUserLambda = new PythonFunction(this, 'DescribeUserLambda', {
      description: 'Describes a given user',
      runtime: lambda.Runtime.PYTHON_3_8,
      architecture: lambda.Architecture.ARM_64,
      entry: path.join('lambda', 'describe_user'),
      index: 'index.py',
      handler: 'lambda_handler',
      layers: [libActivityPub, libCommons, libMumble],
      environment: {
        USER_TABLE_NAME: userTable.userTable.tableName,
        // TODO: specify DOMAIN_NAME in production
      },
      memorySize: 128,
      timeout: Duration.seconds(10),
    });
    userTable.userTable.grantReadData(describeUserLambda);
    // - receives an activity posted to the inbox of a given user
    const receiveInboundActivityLambda = new PythonFunction(
      this,
      'ReceiveInboundActivityLambda',
      {
        description: 'Receives an activity posted to the inbox of a given user',
        runtime: lambda.Runtime.PYTHON_3_8,
        architecture: lambda.Architecture.ARM_64,
        entry: path.join('lambda', 'receive_inbound_activity'),
        index: 'index.py',
        handler: 'lambda_handler',
        layers: [libActivityPub, libCommons, libMumble],
        environment: {
          USER_TABLE_NAME: userTable.userTable.tableName,
          OBJECTS_BUCKET_NAME: objectStore.objectsBucket.bucketName,
          // TODO: specify DOMAIN_NAME in production
        },
        memorySize: 256,
        timeout: Duration.seconds(20),
      },
    );
    userTable.userTable.grantReadData(receiveInboundActivityLambda);
    objectStore.grantPutIntoInbox(receiveInboundActivityLambda);
    // - returns activites in the outbox of a given user
    const getOutboxActivitiesLambda = new PythonFunction(
      this,
      'GetOutboxActivitiesLambda',
      {
        description: 'Returns activities in the outbox of a given user',
        runtime: lambda.Runtime.PYTHON_3_8,
        architecture: lambda.Architecture.ARM_64,
        entry: path.join('lambda', 'get_outbox_activities'),
        index: 'index.py',
        handler: 'lambda_handler',
        layers: [libActivityPub, libCommons, libMumble],
        environment: {
          USER_TABLE_NAME: userTable.userTable.tableName,
          OBJECT_TABLE_NAME: objectStore.objectTable.tableName,
          OBJECTS_BUCKET_NAME: objectStore.objectsBucket.bucketName,
          DOMAIN_NAME_PARAMETER_PATH:
            systemParameters.domainNameParameter.parameterName,
        },
        memorySize: 256,
        timeout: Duration.seconds(20),
      },
    );
    userTable.userTable.grantReadData(getOutboxActivitiesLambda);
    objectStore.objectTable.grantReadData(getOutboxActivitiesLambda);
    objectStore.grantGetFromOutbox(getOutboxActivitiesLambda);
    systemParameters.domainNameParameter.grantRead(getOutboxActivitiesLambda);
    // - returns the follower of a given user
    const getFollowersLambda = new PythonFunction(
      this,
      'GetFollowersLambda',
      {
        description: 'Returns the followers of a given user',
        runtime: lambda.Runtime.PYTHON_3_8,
        architecture: lambda.Architecture.ARM_64,
        entry: path.join('lambda', 'get_followers'),
        index: 'index.py',
        handler: 'lambda_handler',
        layers: [libActivityPub, libCommons, libMumble],
        environment: {
          USER_TABLE_NAME: userTable.userTable.tableName,
          DOMAIN_NAME_PARAMETER_PATH:
            systemParameters.domainNameParameter.parameterName,
        },
        memorySize: 256,
        timeout: Duration.seconds(20),
      },
    );
    userTable.userTable.grantReadData(getFollowersLambda);
    systemParameters.domainNameParameter.grantRead(getFollowersLambda);
    // - returns accounts followed by a given user
    const getFollowingLambda = new PythonFunction(
      this,
      'GetFollowingLambda',
      {
        description: 'Returns accounts followed by a given user',
        runtime: lambda.Runtime.PYTHON_3_8,
        architecture: lambda.Architecture.ARM_64,
        entry: path.join('lambda', 'get_following'),
        index: 'index.py',
        handler: 'lambda_handler',
        layers: [libActivityPub, libCommons, libMumble],
        environment: {
          USER_TABLE_NAME: userTable.userTable.tableName,
          DOMAIN_NAME_PARAMETER_PATH:
            systemParameters.domainNameParameter.parameterName,
        },
        memorySize: 256,
        timeout: Duration.seconds(20),
      },
    );
    userTable.userTable.grantReadData(getFollowingLambda);
    systemParameters.domainNameParameter.grantRead(getFollowingLambda);
    // - returns a specified post object of a given user
    const getPostLambda = new PythonFunction(
      this,
      'GetPostLambda',
      {
        description: 'Returns a specified object of a given user',
        runtime: lambda.Runtime.PYTHON_3_8,
        architecture: lambda.Architecture.ARM_64,
        entry: path.join('lambda', 'get_post'),
        index: 'index.py',
        handler: 'lambda_handler',
        layers: [libActivityPub, libCommons, libMumble],
        environment: {
          OBJECT_TABLE_NAME: objectStore.objectTable.tableName,
          OBJECTS_BUCKET_NAME: objectStore.objectsBucket.bucketName,
        },
        memorySize: 256,
        timeout: Duration.seconds(20),
      },
    );
    objectStore.objectTable.grantReadData(getPostLambda);
    objectStore.grantGetFromObjectsFolder(getPostLambda);
    // - returns replies to a specific post object
    const getPostRepliesLambda = new PythonFunction(
      this,
      'GetPostRepliesLambda',
      {
        description: 'Returns replies to a specific post',
        runtime: lambda.Runtime.PYTHON_3_8,
        architecture: lambda.Architecture.ARM_64,
        entry: path.join('lambda', 'get_post_replies'),
        index: 'index.py',
        handler: 'lambda_handler',
        layers: [libActivityPub, libCommons, libMumble],
        environment: {
          OBJECT_TABLE_NAME: objectStore.objectTable.tableName,
        },
        memorySize: 256,
        timeout: Duration.seconds(20),
      },
    );
    objectStore.objectTable.grantReadData(getPostRepliesLambda);

    // the API
    this.api = new RestApiWithSpec(this, `mumble-api-${deploymentStage}`, {
      description: `Mumble endpoints API (${deploymentStage})`,
      openApiInfo: {
        version: '0.0.1',
      },
      openApiOutputPath: path.join('openapi', `api-${deploymentStage}.json`),
      deploy: true,
      deployOptions: {
        stageName: 'staging',
        description: 'Default deployment',
        loggingLevel: apigateway.MethodLoggingLevel.INFO,
        // TODO: set different limit in production
        throttlingBurstLimit: 50,
        throttlingRateLimit: 100,
      },
    });

    // models
    // - WebFinger response
    const webFingerModel = this.api.addModel('WebFinger', {
      description: 'WebFinger response',
      contentType: 'application/json',
      schema: {
        schema: apigateway.JsonSchemaVersion.DRAFT4,
        title: 'WebFinger',
        description: 'WebFinter response',
        type: apigateway.JsonSchemaType.OBJECT,
        properties: {
          subject: {
            description: 'Subject URI',
            type: apigateway.JsonSchemaType.STRING,
            example: 'acct:kemoto@mumble.codemonger.io',
          },
          links: {
            description: 'Links associated with the subject',
            type: apigateway.JsonSchemaType.ARRAY,
            items: {
              description: 'Link item',
              type: apigateway.JsonSchemaType.OBJECT,
              properties: {
                rel: {
                  description: 'Relation type of the linked object',
                  type: apigateway.JsonSchemaType.STRING,
                  example: 'self',
                },
                type: {
                  description: 'Media type of the linked object',
                  type: apigateway.JsonSchemaType.STRING,
                  example: 'application/activity+json',
                },
                href: {
                  description: 'URI of the linked object',
                  type: apigateway.JsonSchemaType.STRING,
                  example: 'https://mumble.codemonger.io/users/kemoto',
                },
                // TODO: add titles
                // TODO: properties
              },
              required: ['rel'],
            },
          },
          // TODO: add aliases
          // TODO: add properties
        },
        required: ['subject'],
      },
    });
    // - Actor response
    const actorModel = this.api.addModel('Actor', {
      description: 'Actor response',
      contentType: 'application/activity+json',
      schema: {
        schema: apigateway.JsonSchemaVersion.DRAFT4,
        title: 'Actor',
        description: 'Actor response',
        type: apigateway.JsonSchemaType.OBJECT,
        properties: {
          '@context': {
            description: 'JSON-LD context',
            type: apigateway.JsonSchemaType.STRING,
            example: 'https://www.w3.org/ns/activitystreams',
          },
          id: {
            description: 'ID of the object',
            type: apigateway.JsonSchemaType.STRING,
            example: 'https://mumble.codemonger.io/users/kemoto',
          },
          type: {
            description: 'Object type. Always "Person"',
            type: apigateway.JsonSchemaType.STRING,
            enum: ['Person'],
            example: 'Person',
          },
          name: {
            description: 'Preferred "nickname" or "display name" of the actor',
            type: apigateway.JsonSchemaType.STRING,
            example: 'Kikuo Emoto',
          },
          preferredUsername: {
            description: 'Short username which may be used to refer to the actor, with no uniqueness guarantees',
            type: apigateway.JsonSchemaType.STRING,
            example: 'kemoto',
          },
          summary: {
            description: 'Quick summary or bio by the user about themselves',
            type: apigateway.JsonSchemaType.STRING,
            example: 'The representative of codemonger',
          },
          url: {
            description: 'Link to the actor\'s "profile web page", if not equal to the value of id',
            type: apigateway.JsonSchemaType.STRING,
            example: 'https://codemonger.io',
          },
          inbox: {
            description: 'Inbox URI',
            type: apigateway.JsonSchemaType.STRING,
            example: 'https://mumble.codemonger.io/users/kemoto/inbox',
          },
          outbox: {
            description: 'Outbox URI',
            type: apigateway.JsonSchemaType.STRING,
            example: 'https://mumble.codemonger.io/users/kemoto/outbox',
          },
          following: {
            description: 'Following list URI',
            type: apigateway.JsonSchemaType.STRING,
            example: 'https://mumble.codemonger.io/users/kemoto/following',
          },
          followers: {
            description: 'Follower list URI',
            type: apigateway.JsonSchemaType.STRING,
            example: 'https://mumble.codemonger.io/users/kemoto/followers',
          },
          publicKey: {
            // required by Mastodon
            description: 'Public key',
            type: apigateway.JsonSchemaType.OBJECT,
            properties: {
              id: {
                description: 'ID of the public key',
                type: apigateway.JsonSchemaType.STRING,
                example: 'https://mumble.codemonger.io/users/kemoto#main-key',
              },
              owner: {
                description: 'Owner of the public key',
                type: apigateway.JsonSchemaType.STRING,
                example: 'https://mumble.codemonger.io/users/kemoto',
              },
              publicKeyPem: {
                description: 'PEM representation of the public key',
                type: apigateway.JsonSchemaType.STRING,
                example: '-----BEGIN PUBLIC KEY-----\n...',
              },
            },
            required: ['id', 'owner', 'publicKeyPem'],
          },
        },
        required: [
          '@context',
          'followers',
          'following',
          'id',
          'inbox',
          'outbox',
          'publicKey',
          'type',
        ],
      },
    });
    // - Object
    const objectModel = this.api.addModel('Object', {
      description: 'Object',
      contentType: 'application/activity+json',
      schema: {
        schema: apigateway.JsonSchemaVersion.DRAFT4,
        title: 'object',
        description: 'Object',
        type: apigateway.JsonSchemaType.OBJECT,
        properties: {
          id: {
            description: 'ID of the object',
            type: apigateway.JsonSchemaType.STRING,
            example: 'https://mumble.codemonger.io/users/kemoto/posts/abcdefghijklmn',
          },
          type: {
            description: 'Type of the object',
            type: apigateway.JsonSchemaType.STRING,
            example: 'Note',
          },
        },
      },
    });
    // - Activity
    const activityModel = this.api.addModel('Activity', {
      description: 'Activity',
      contentType: 'application/activity+json',
      schema: {
        schema: apigateway.JsonSchemaVersion.DRAFT4,
        title: 'activity',
        description: 'Activity',
        type: apigateway.JsonSchemaType.OBJECT,
        properties: {
          id: {
            description: 'ID of the activity',
            type: apigateway.JsonSchemaType.STRING,
            example: 'https://mumble.codemonger.io/users/kemoto/activities/abcdefghijklmn',
          },
          type: {
            description: 'Type of the activity',
            type: apigateway.JsonSchemaType.STRING,
            example: 'Create',
          },
          actor: {
            description: 'Actor of the activity',
            type: apigateway.JsonSchemaType.STRING,
            example: 'https://mumble.codemonger.io/users/kemoto',
          },
          object: {
            description: 'Object of the activity',
            oneOf: [
              {
                description: 'ID of the object',
                type: apigateway.JsonSchemaType.STRING,
                example: 'https://mumble.codemonger.io/users/kemoto/posts/abcdefghijklmn',
              },
              {
                description: 'Object',
                modelRef: objectModel,
              },
            ],
          },
        },
        required: ['type', 'actor'],
      },
    });
    // - OrderedCollection
    const orderedCollectionModel = this.api.addModel('OrderedCollection', {
      description: 'Ordered collection of items',
      contentType: 'application/activity+json',
      schema: {
        schema: apigateway.JsonSchemaVersion.DRAFT4,
        title: 'orderedCollection',
        description: 'Ordered collection of items',
        type: apigateway.JsonSchemaType.OBJECT,
        properties: {
          '@context': {
            description: 'JSON-LD context',
            type: apigateway.JsonSchemaType.STRING,
            example: 'https://www.w3.org/ns/activitystreams',
          },
          id: {
            description: 'ID of the collection',
            type: apigateway.JsonSchemaType.STRING,
            example: 'https://mumble.codmonger.io/users/kemoto/followers',
          },
          type: {
            description: 'ActivityStreams object type',
            type: apigateway.JsonSchemaType.STRING,
            example: 'OrderedCollection',
          },
          first: {
            description: 'ID of the first page of the collection',
            type: apigateway.JsonSchemaType.STRING,
            example: 'https://mumble.codemonger.io/users/kemoto/followers?page=true',
          },
          totalItems: {
            description: 'Total number of items in the collection',
            type: apigateway.JsonSchemaType.INTEGER,
            minimum: 0,
            example: 123,
          },
        },
        required: ['@context', 'id', 'type', 'first'],
      },
    });
    const orderedCollectionPageModel = this.api.addModel(
      'OrderedCollectionPage',
      {
        description: 'Page in an ordered collection of items',
        contentType: 'application/activity+json',
        schema: {
          schema: apigateway.JsonSchemaVersion.DRAFT4,
          title: 'orderedCollectionPage',
          description: 'Page in an ordered collection of items',
          type: apigateway.JsonSchemaType.OBJECT,
          properties: {
            '@context': {
              description: 'JSON-LD context',
              type: apigateway.JsonSchemaType.STRING,
              example: 'https://www.w3.org/ns/activitystreams',
            },
            id: {
              description: 'ID of the collection page',
              type: apigateway.JsonSchemaType.STRING,
              example: 'https://mumble.codemonger.io/users/kemoto/followers?page=true',
            },
            type: {
              description: 'ActivityStreams type of the collection page',
              type: apigateway.JsonSchemaType.STRING,
              example: 'OrderedCollectionPage',
            },
            partOf: {
              description: 'ID of the collection containing the page',
              type: apigateway.JsonSchemaType.STRING,
              example: 'https://mumble.codemonger.io/users/kemoto/followers',
            },
            orderedItems: {
              description: 'Items in the collection page',
              type: apigateway.JsonSchemaType.ARRAY,
            },
            totalItems: {
              description: 'Total number of items in the collection',
              type: apigateway.JsonSchemaType.INTEGER,
              minimum: 0,
              example: 123,
            },
            prev: {
              description: 'ID of the previous collection page',
              type: apigateway.JsonSchemaType.STRING,
              example: 'https://mumble.codemonger.io/users/kemoto/followers?page=true&before=https%3A%2F%2Fmastodon.social%2Fusers%2FGargron',
            },
            next: {
              description: 'ID of the next collection page',
              type: apigateway.JsonSchemaType.STRING,
              example: 'https://mumble.codemonger.io/users/kemoto/followers?page=true&after=https%3A%2F%2Fmastodon.social%2Fusers%2FGargron',
            },
          },
          required: ['@context', 'id', 'type', 'partOf', 'orderedItems'],
        },
      },
    );
    // - Paginated
    const paginatedModel = this.api.addModel('Paginated', {
      description: 'Paginated response that may be either of an OrderedCollection or OrderedCollectionPage',
      contentType: 'application/activity+json',
      schema: {
        schema: apigateway.JsonSchemaVersion.DRAFT4,
        title: 'paginated',
        description: 'Paginated response that may be an OrderedCollection or OrderedCollectionPage',
        oneOf: [
          {
            description: 'OrderedCollection',
            modelRef: orderedCollectionModel,
          },
          {
            description: 'OrderedCollectionPage',
            modelRef: orderedCollectionPageModel,
          },
        ],
      },
    });

    // request validator
    const requestValidator = new apigateway.RequestValidator(
      this,
      'RequestValidator',
      {
        restApi: this.api,
        validateRequestBody: true,
        validateRequestParameters: true,
      },
    );

    // mapping template components
    function urlParameterField(name: string): MappingTemplateItem {
      return [
        name,
        `"$util.escapeJavaScript($util.urlDecode($input.params('${name}'))).replaceAll("\\'", "'")"`,
      ];
    }
    const mappingTemplates: { [name: string]: MappingTemplateItem } = {
      resource: [
        'resource',
        `"$util.escapeJavaScript($util.urlDecode($input.params('resource'))).replaceAll("\\'", "'")"`,
      ],
      username: [
        'username',
        `"$util.escapeJavaScript($util.urlDecode($input.params('username'))).replaceAll("\\'", "'")"`,
      ],
      uniquePart: urlParameterField('uniquePart'),
      signature: [
        'signature',
        `"$util.escapeJavaScript($input.params('signature')).replaceAll("\\'", "'")"`,
      ],
      date: [
        'date',
        `"$util.escapeJavaScript($input.params('x-signature-date')).replaceAll("\\'", "'")"`,
      ],
      digest: [
        'digest',
        `"$util.escapeJavaScript($input.params('digest')).replaceAll("\\'", "'")"`,
      ],
      contentType: [
        'contentType',
        `"$util.escapeJavaScript($input.params('content-type')).replaceAll("\\'", "'")"`,
      ],
      body: [
        'body',
        `"$util.escapeJavaScript($input.body).replaceAll("\\'","'")"`,
      ],
      apiDomainName: ifThenElse(
        '$input.params("x-host-header") != ""',
        [[
          'apiDomainName',
          `"$util.escapeJavaScript($input.params('x-host-header')).replaceAll("\\'", "'")"`,
        ]],
        [[
          'apiDomainName',
          '"$context.domainName"',
        ]],
      ),
      page: ifThen(
        '$input.params("page") != ""',
        [[
          'page',
          '$util.escapeJavaScript($input.params("page"))',
        ]],
      ),
      after: ifThen(
        '$input.params("after") != ""',
        [[
          'after',
          `"$util.escapeJavaScript($util.urlDecode($input.params("after"))).replaceAll("\\'", "¶")"`,
        ]],
      ),
      before: ifThen(
        '$input.params("before") != ""',
        [[
          'before',
          `"$util.escapeJavaScript($util.urlDecode($input.params("before"))).replaceAll("\\'", "'")"`,
        ]],
      ),
    };

    // /.well-known
    const well_known = this.api.root.addResource('.well-known');
    // /.well-known/webfinger
    const webfinger = well_known.addResource('webfinger')
    // - GET: resolves the account information
    webfinger.addMethod(
      'GET',
      new apigateway.LambdaIntegration(webFingerLambda, {
        proxy: false,
        passthroughBehavior: apigateway.PassthroughBehavior.NEVER,
        requestTemplates: {
          // X-Host-Header is given if the request comes from the CloudFront
          // distribution (only in development), and it must be used to verify
          // the requested domain (`apiDomainName`).
          // Otherwise, `apiDomainName` equals that of API Gateway.
          // DO NOT rely on `apiDomainName` in production
          // TODO: add rel
          'application/json': composeMappingTemplate([
            mappingTemplates.resource,
            mappingTemplates.apiDomainName,
          ]),
        },
        integrationResponses: [
          catchErrorsWith(404, 'UnexpectedDomainError', 'NotFoundError'),
          catchErrorsWith(400, 'BadRequestError'),
          catchErrorsWith(500, 'BadConfigurationError'),
          {
            statusCode: '200',
          },
        ],
      }),
      {
        operationName: 'webFinger',
        description: 'Returns the information on a given user',
        requestParameterSchemas: {
          'method.request.querystring.resource': {
            description: 'Account to be WebFingered',
            required: true,
            schema: {
              type: 'string',
            },
            example: 'acct%3Akemoto%40mumble.codemonger.io',
          },
          // TODO: add rel
        },
        requestValidator,
        methodResponses: [
          {
            statusCode: '200',
            description: 'successful operation',
            responseModels: {
              'application/json': webFingerModel,
            },
          },
          {
            statusCode: '400',
            description: 'account is invalid',
          },
          {
            statusCode: '404',
            description: 'account is not found',
          },
          {
            statusCode: '500',
            description: 'internal server error',
          },
        ],
      },
    );
    // /users
    const users = this.api.root.addResource('users');
    // /users/{user_id}
    const user = users.addResource('{username}');
    // - GET: returns the actor information
    user.addMethod(
      'GET',
      new apigateway.LambdaIntegration(describeUserLambda, {
        proxy: false,
        passthroughBehavior: apigateway.PassthroughBehavior.NEVER,
        requestTemplates: {
          // `apiDomainName`: X-Host-Header is given if the request comes from
          // the CloudFront distribution (only in development). Otherwise, use
          // Host.
          // DO NOT rely on `apiDomainName` in production
          'application/json': composeMappingTemplate([
            mappingTemplates.username,
            mappingTemplates.apiDomainName,
          ]),
        },
        integrationResponses: [
          catchErrorsWith(404, 'NotFoundError'),
          catchErrorsWith(429, 'TooManyAccessError'),
          catchErrorsWith(500, 'BadConfigurationError'),
          {
            statusCode: '200',
          },
        ],
      }),
      {
        operationName: 'describeUser',
        description: 'Returns the actor object of a given user',
        requestParameterSchemas: {
          'method.request.path.username': {
            description: 'Username to be described',
            required: true,
            schema: {
              type: 'string',
            },
            example: 'kemoto',
          },
        },
        requestValidator,
        methodResponses: [
          {
            statusCode: '200',
            description: 'successful operation',
            responseModels: {
              'application/activity+json': actorModel,
              'application/ld+json': actorModel,
            },
          },
          {
            statusCode: '404',
            description: 'user is not found',
          },
          {
            statusCode: '429',
            description: 'there are too many requests',
          },
          {
            statusCode: '500',
            description: 'internal server error',
          },
        ],
      },
    );
    // /users/{username}/inbox
    const inbox = user.addResource('inbox');
    // - POST: posts an activity to the inbox of a given user
    inbox.addMethod(
      'POST',
      new apigateway.LambdaIntegration(receiveInboundActivityLambda, {
        proxy: false,
        passthroughBehavior: apigateway.PassthroughBehavior.NEVER,
        requestTemplates: {
          // `apiDomainName`: X-Host-Header is given if the request comes from
          // the CloudFront distribution (only in development). Otherwise, use
          // Host.
          // DO NOT rely on `apiDomainName` in production
          'application/activity+json': composeMappingTemplate([
            mappingTemplates.username,
            mappingTemplates.signature,
            mappingTemplates.date,
            mappingTemplates.digest,
            mappingTemplates.contentType,
            mappingTemplates.body,
            mappingTemplates.apiDomainName,
          ]),
          // TODO: support application/ld+json
        },
        integrationResponses: [
          catchErrorsWith(400, 'BadRequestError'),
          catchErrorsWith(401, 'UnauthorizedError'),
          catchErrorsWith(403, 'ForbiddenError'),
          catchErrorsWith(404, 'NotFoundError'),
          catchErrorsWith(500, 'BadConfigurationError'),
          {
            statusCode: '200',
          },
        ],
      }),
      {
        operationName: 'postActivity',
        description: 'Posts an activity to the inbox of a given user',
        requestParameterSchemas: {
          'method.request.path.username': {
            description: 'Username to receive a posted activity',
            required: true,
            schema: {
              type: 'string',
            },
            example: 'kemoto',
          },
        },
        requestModels: {
          'application/activity+json': activityModel,
          'application/ld+json': activityModel,
        },
        requestValidator,
        methodResponses: [
          {
            statusCode: '200',
            description: 'successful operation',
          },
          {
            statusCode: '400',
            description: 'request is malformed',
          },
          {
            statusCode: '401',
            description: 'request has no valid signature',
          },
          {
            statusCode: '403',
            description: 'requestor is not allowed to post',
          },
          {
            statusCode: '404',
            description: 'user is not found',
          },
          {
            statusCode: '500',
            description: 'internal server error',
          },
        ],
      },
    );
    // /users/{username}/outbox
    const outbox = user.addResource('outbox');
    // - GET: returns activities of a given user
    outbox.addMethod(
      'GET',
      new apigateway.LambdaIntegration(getOutboxActivitiesLambda, {
        proxy: false,
        passthroughBehavior: apigateway.PassthroughBehavior.NEVER,
        requestTemplates: {
          'application/json': composeMappingTemplate([
            mappingTemplates.username,
            mappingTemplates.page,
            mappingTemplates.after,
            mappingTemplates.before,
          ]),
        },
        integrationResponses: [
          catchErrorsWith(400, 'BadRequestError'),
          catchErrorsWith(404, 'NotFoundError'),
          catchErrorsWith(429, 'TooManyAccessError'),
          catchErrorsWith(500, 'CorruptedDataError'),
          {
            statusCode: '200',
          },
        ],
      }),
      {
        operationName: 'getActivities',
        description: 'Returns activities of a given user',
        requestParameterSchemas: {
          'method.request.path.username': {
            description: 'Username whose activities are to be obtained',
            required: true,
            schema: {
              type: 'string',
            },
            example: 'kemoto',
          },
          'method.request.querystring.page': {
            description: 'Whether to obtain a page of activities',
            required: false,
            schema: {
              type: 'boolean',
              default: false,
            },
            example: 'true',
          },
          'method.request.querystring.after': {
            description: 'Obtains activities after this ID',
            required: false,
            schema: {
              type: 'string',
            },
          },
          'method.request.querystring.before': {
            description: 'Obtains activities before this ID',
            required: false,
            schema: {
              type: 'string',
            },
          },
        },
        requestValidator,
        methodResponses: [
          {
            statusCode: '200',
            description: 'successful operation',
            responseModels: {
              'application/activity+json': paginatedModel,
              'application/ld+json': paginatedModel,
            },
          },
          {
            statusCode: '400',
            description: 'request is malformed',
          },
          {
            statusCode: '404',
            description: 'user is not found',
          },
          {
            statusCode: '429',
            description: 'there are too many requests',
          },
          {
            statusCode: '500',
            description: 'internal server error',
          },
        ],
      },
    );
    // /users/{username}/followers
    const followers = user.addResource('followers');
    // - GET: returns the followers of a given user
    followers.addMethod(
      'GET',
      new apigateway.LambdaIntegration(getFollowersLambda, {
        proxy: false,
        passthroughBehavior: apigateway.PassthroughBehavior.NEVER,
        requestTemplates: {
          'application/json': composeMappingTemplate([
            mappingTemplates.username,
            mappingTemplates.page,
            mappingTemplates.after,
            mappingTemplates.before,
          ]),
        },
        integrationResponses: [
          catchErrorsWith(400, 'BadRequestError'),
          catchErrorsWith(404, 'NotFoundError'),
          {
            statusCode: '200',
          },
        ],
      }),
      {
        operationName: 'getFollowers',
        description: 'Returns the followers of a given user',
        requestParameterSchemas: {
          'method.request.path.username': {
            description: 'Username whose followers are to be obtained',
            required: true,
            schema: {
              type: 'string',
            },
            example: 'kemoto',
          },
          'method.request.querystring.page': {
            description: 'Whether to obtain a page of followers',
            required: false,
            schema: {
              type: 'boolean',
              default: 'false',
            },
            example: 'true',
          },
          'method.request.querystring.after': {
            description: 'Obtains followers after this ID',
            required: false,
            schema: {
              type: 'string',
            },
            example: 'https%3A%2F%2Fmumble.codemonger.io%2Fusers%2Fkemoto',
          },
          'method.request.querystring.before': {
            description: 'Obtains followers before this ID',
            required: false,
            schema: {
              type: 'string',
            },
            example: 'https%3A%2F%2Fmumble.codemonger.io%2Fusers%2Fkemoto',
          },
        },
        requestValidator,
        methodResponses: [
          {
            statusCode: '200',
            description: 'successful operation',
            responseModels: {
              'application/activity+json': paginatedModel,
              'application/ld+json': paginatedModel,
            },
          },
          {
            statusCode: '400',
            description: 'request is malformed',
          },
          {
            statusCode: '404',
            description: 'user is not found',
          },
        ],
      },
    );
    // /users/{username}/following
    const following = user.addResource('following');
    // - GET: returns acounts followed by a given user
    following.addMethod(
      'GET',
      new apigateway.LambdaIntegration(getFollowingLambda, {
        proxy: false,
        passthroughBehavior: apigateway.PassthroughBehavior.NEVER,
        requestTemplates: {
          'application/json': composeMappingTemplate([
            mappingTemplates.username,
            mappingTemplates.page,
            mappingTemplates.after,
            mappingTemplates.before,
          ]),
        },
        integrationResponses: [
          catchErrorsWith(400, 'BadRequestError'),
          catchErrorsWith(404, 'NotFoundError'),
          catchErrorsWith(429, 'TooManyAccessError'),
          {
            statusCode: '200',
          },
        ],
      }),
      {
        operationName: 'getFollowing',
        description: 'Returns accounts followed by a given user.',
        requestValidator,
        requestParameterSchemas: {
          'method.request.path.username': {
            description: 'Username whose following accounts are to be obtained',
            required: true,
            schema: {
              type: 'string',
            },
            example: 'kemoto',
          },
          'method.request.querystring.page': {
            description: 'Whether to obtain a page of following accounts',
            required: false,
            schema: {
              type: 'boolean',
              default: false,
            },
            example: true,
          },
          'method.request.querystring.after': {
            description: 'Obtains following accounts after this ID',
            required: false,
            schema: {
              type: 'string',
            },
            example: 'https%3A%2F%2Fmumble.codemonger.io%2Fusers%2Fkemoto',
          },
          'method.request.querystring.before': {
            description: 'Obtains following accounts before this ID',
            required: false,
            schema: {
              type: 'string',
            },
            example: 'https%3A%2F%2Fmumble.codemonger.io%2Fusers%2Fkemoto',
          },
        },
        methodResponses: [
          {
            statusCode: '200',
            description: 'successful operation',
            responseModels: {
              'application/activity+json': paginatedModel,
              'application/ld+json': paginatedModel,
            },
          },
          {
            statusCode: '400',
            description: 'request is malformed',
          },
          {
            statusCode: '404',
            description: 'user is not found',
          },
          {
            statusCode: '429',
            description: 'there are too many requests',
          },
        ],
      },
    );
    // /users/{username}/posts
    const posts = user.addResource('posts');
    // /users/{username}/posts/{uniquePart}
    const post = posts.addResource('{uniquePart}')
    // - GET: returns a specified post object
    post.addMethod(
      'GET',
      new apigateway.LambdaIntegration(getPostLambda, {
        proxy: false,
        passthroughBehavior: apigateway.PassthroughBehavior.NEVER,
        requestTemplates: {
          'application/json': composeMappingTemplate([
            mappingTemplates.username,
            mappingTemplates.uniquePart,
          ]),
        },
        integrationResponses: [
          catchErrorsWith(400, 'BadRequestError'),
          catchErrorsWith(404, 'NotFoundError'),
          catchErrorsWith(429, 'TooManyAccessError'),
          catchErrorsWith(500, 'CorruptedDataError'),
          {
            statusCode: '200',
          },
        ],
      }),
      {
        operationName: 'getPost',
        description: 'Returns an object representing a post',
        requestParameterSchemas: {
          'method.request.path.username': {
            description: 'Username whose post is to be obtained',
            required: true,
            schema: {
              type: 'string',
            },
            example: 'kemoto',
          },
          'method.request.path.uniquePart': {
            description: "Unique part of the ID of the post object to be obtained",
            required: true,
            schema: {
              type: 'string',
            },
            example: '01234567-89ab-cdef-0123-456789abcdef',
          },
        },
        requestValidator,
        methodResponses: [
          {
            statusCode: '200',
            description: 'successful operation',
            responseModels: {
              'application/activity+json': objectModel,
              'application/ld+json': objectModel,
            },
          },
          {
            statusCode: '400',
            description: 'request is malformed',
          },
          {
            statusCode: '404',
            description: 'user or post is not found',
          },
          {
            statusCode: '429',
            description: 'there are too many requests',
          },
          {
            statusCode: '500',
            description: 'internal server error',
          },
        ],
      },
    );
    // /users/{username}/posts/{uniquePart}/replies
    const replies = post.addResource('replies');
    // - GET: returns a collection of replies to a specific post
    replies.addMethod(
      'GET',
      new apigateway.LambdaIntegration(getPostRepliesLambda, {
        proxy: false,
        passthroughBehavior: apigateway.PassthroughBehavior.NEVER,
        requestTemplates: {
          'application/json': composeMappingTemplate([
            mappingTemplates.username,
            mappingTemplates.uniquePart,
            mappingTemplates.page,
            mappingTemplates.after,
            mappingTemplates.before,
          ]),
        },
        integrationResponses: [
          catchErrorsWith(400, 'BadRequestError'),
          catchErrorsWith(404, 'NotFoundError'),
          catchErrorsWith(429, 'TooManyAccessError'),
          catchErrorsWith(500, 'BadConfigurationError'),
          {
            statusCode: '200',
          },
        ],
      }),
      {
        operationName: 'getPostReplies',
        description: 'Returns a collection of replies to a specific post',
        requestParameterSchemas: {
          'method.request.path.username': {
            description: 'Username who owns the post that got replied',
            required: true,
            schema: {
              type: 'string',
            },
            example: 'kemoto',
          },
          'method.request.path.uniquePart': {
            description: 'Unique part of the ID of the post that got replied',
            required: true,
            schema: {
              type: 'string',
            },
            example: '01234567-89ab-cdef-0123-456789abcdef',
          },
          'method.request.querystring.page': {
            description: 'Whether to obtain a collection page of replies',
            required: false,
            schema: {
              type: 'boolean',
              default: false,
            },
            example: true,
          },
          'method.request.querystring.after': {
            description: 'Obtains replies after this ID',
            required: false,
            schema: {
              type: 'string',
            },
            example: '2023-05-19T04%3A06%3A41Z%3Ahttps%3A%2F%2Fmumble.codemonger.io%2Fusers%2Fkemoto%2Fposts%2F01234567-89ab-cdef-0123-456789abcdef',
          },
          'method.request.querystring.before': {
            description: 'Obtains replies before this ID',
            required: false,
            schema: {
              type: 'string',
            },
            example: '2023-05-19T04%3A06%3A41Z%3Ahttps%3A%2F%2Fmumble.codemonger.io%2Fusers%2Fkemoto%2Fposts%2F01234567-89ab-cdef-0123-456789abcdef',
          },
        },
        requestValidator,
        methodResponses: [
          {
            statusCode: '200',
            description: 'successful operation',
            responseModels: {
              'application/activity+json': paginatedModel,
              'application/ld+json': paginatedModel,
            },
          },
          {
            statusCode: '400',
            description: 'request is malformed',
          },
          {
            statusCode: '404',
            description: 'user or post does not exist',
          },
          {
            statusCode: '429',
            description: 'there are too many requests',
          },
          {
            statusCode: '500',
            description: 'internal server error',
          },
        ],
      },
    );

    // configures the CloudFront distribution
    // - cache policy
    const forwardedHeaders = [
      'X-Signature-Date', // Date should not be cached. this header exists only if the request has a Signature
      'Digest',
      'Signature',
    ]; // these headers are also cached
    if (deploymentStage === 'development') {
      // X-Host-Header must be forwarded in development
      forwardedHeaders.push('X-Host-Header');
    }
    const cachePolicy = new cloudfront.CachePolicy(
      this,
      'MumbleApiCachePolicy',
      {
        comment: `Mumble API cache policy (${deploymentStage})`,
        // X-Host-Header must be forwarded in development
        headerBehavior:
          cloudfront.CacheHeaderBehavior.allowList(...forwardedHeaders),
        // TODO: should we narrow query strings?
        queryStringBehavior: cloudfront.CacheQueryStringBehavior.all(),
        // TODO: set longer duration for production
        defaultTtl: Duration.seconds(30),
      },
    );
    // - CloudFront functions (provided only in development)
    const requestHandlerFunctions: FunctionProps[] = [
      // forwards Date header to the origin as X-Signature-Date
      {
        filePath: path.join('cloudfront-fn', 'forward-date-header.js'),
        handler: 'forwardDateHeader',
      },
    ];
    if (deploymentStage === 'development') {
      // forwards Host header to the origin as X-Host-Header
      requestHandlerFunctions.push({
        filePath: path.join('cloudfront-fn', 'forward-host-header.js'),
        handler: 'forwardHostHeader',
      });
    }
    // - distribution
    this.distribution = new cloudfront.Distribution(
      this,
      `MumbleApiDistribution`,
      {
        comment: `Mumble API distribution (${deploymentStage})`,
        defaultBehavior: {
          origin: new origins.RestApiOrigin(this.api),
          cachePolicy,
          allowedMethods: cloudfront.AllowedMethods.ALLOW_ALL,
          viewerProtocolPolicy: cloudfront.ViewerProtocolPolicy.HTTPS_ONLY,
          functionAssociations: [
            {
              eventType: cloudfront.FunctionEventType.VIEWER_REQUEST,
              function: new cloudfront.Function(
                this,
                'ProcessRequestCF',
                {
                  comment: 'Processes requests',
                  code: new BundledCode(...requestHandlerFunctions),
                },
              ),
            },
          ],
        },
        enableLogging: true,
        // TODO: set domain name and certificate for production
      },
    );
  }
}

// Generates integration response to catch specific errors from Lambda.
//
// Returned object may be an item of `integrationResponses`.
function catchErrorsWith(
  statusCode: string | number,
  ...errors: string[]
): apigateway.IntegrationResponse {
  return {
    selectionPattern: `(${errors.join('|')})\\(.+\\)`,
    statusCode: statusCode.toString(),
    responseTemplates: {
      'application/json': '{"message":$input.json("$.errorMessage")}',
    },
  };
}
