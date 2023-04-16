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
