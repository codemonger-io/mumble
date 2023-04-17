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

import { RestApiWithSpec } from 'cdk-rest-api-with-spec';

import type { DeploymentStage } from './deployment-stage';
import type { LambdaDependencies } from './lambda-dependencies';

export interface Props {
  /** Deployment stage. */
  readonly deploymentStage: DeploymentStage;
  /** Lambda dependencies. */
  readonly lambdaDependencies: LambdaDependencies;
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

    const { deploymentStage, lambdaDependencies } = props;
    const { libActivityPub, libMumble } = lambdaDependencies;

    // Lambda functions
    // - responds to a WebFinger request
    const webFingerLambda = new PythonFunction(this, 'WebFingerLambda', {
      description: 'Responds to a WebFinger request',
      runtime: lambda.Runtime.PYTHON_3_8,
      architecture: lambda.Architecture.ARM_64,
      entry: path.join('lambda', 'web_finger'),
      index: 'index.py',
      handler: 'lambda_handler',
      layers: [libActivityPub, libMumble],
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
      layers: [libActivityPub, libMumble],
      memorySize: 128,
      timeout: Duration.seconds(10),
      // TODO: specify DOMAIN_NAME in production
    });

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
          'application/json': `{
            "resource": "$util.escapeJavaScript($util.urlDecode($input.params('resource')))",
            #if ($input.params('x-host-header') != '')
            "apiDomainName": "$util.escapeJavaScript($input.params('x-host-header'))"
            #else
            "apiDomainName": "$context.domainName"
            #end
          }`,
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
          // X-Host-Header is given if the request comes from the CloudFront
          // distribution (only in development). Otherwise, use Host.
          // DO NOT rely on `apiDomainName` in production
          'application/json': `{
            "username": "$util.escapeJavaScript($util.urlDecode($input.params('username')))",
            #if ($input.params('x-host-header') != '')
            "apiDomainName": "$util.escapeJavaScript($util.urlDecode($input.params('x-host-header')))"
            #else
            "apiDomainName": "$context.domainName"
            #end
          }`,
        },
        integrationResponses: [
          catchErrorsWith(404, 'NotFoundError'),
          catchErrorsWith(400, 'BadRequestError'),
          catchErrorsWith(500, 'BadConfigurationError'),
          {
            statusCode: '200',
          },
        ],
      }),
      {
        operationName: 'describeUser',
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
            statusCode: '500',
            description: 'internal server error',
          },
        ],
      },
    );

    // configures the CloudFront distribution
    // - cache policy
    const cachePolicy = new cloudfront.CachePolicy(
      this,
      'MumbleApiCachePolicy',
      {
        comment: `Mumble API cache policy (${deploymentStage})`,
        // X-Host-Header must be forwarded in development
        headerBehavior: deploymentStage === 'development'
          ? cloudfront.CacheHeaderBehavior.allowList('X-Host-Header')
          : undefined,
        // TODO: should we narrow query strings?
        queryStringBehavior: cloudfront.CacheQueryStringBehavior.all(),
        // TODO: set longer duration for production
        defaultTtl: Duration.seconds(30),
      },
    );
    // - CloudFront functions (provided only in development)
    const functionAssociations: cloudfront.FunctionAssociation[] = [];
    if (deploymentStage === 'development') {
      // forwards Host header to the origin as X-Host-Header
      functionAssociations.push(
        {
          eventType: cloudfront.FunctionEventType.VIEWER_REQUEST,
          function: new cloudfront.Function(
            this,
            'ForwardHostHeaderCF',
            {
              comment: 'Forwards the Host header to the origin as X-Host-Header.',
              code: cloudfront.FunctionCode.fromFile({
                filePath: path.join('cloudfront-fn', 'forward-host-header.js'),
              }),
            },
          ),
        },
      );
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
          functionAssociations,
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
