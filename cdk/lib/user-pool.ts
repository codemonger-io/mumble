import {
  Duration,
  Fn,
  RemovalPolicy,
  aws_cognito as cognito,
  aws_iam as iam,
} from "aws-cdk-lib";
import { Construct } from "constructs";

import type { DeploymentStage } from './deployment-stage';
import type { ObjectStore } from './object-store';
import { MEDIA_FOLDER_PREFIX } from './object-store';

/** Properties for {@link UserPool}. */
export interface Props {
  /** Deployment stage. */
  readonly deploymentStage: DeploymentStage;
  /** Object store. */
  readonly objectStore: ObjectStore;
}

/** CDK Construct that provisions the user pool for authentication. */
export class UserPool extends Construct {
  /** User pool. */
  readonly userPool: cognito.UserPool;
  /** Domain of the user pool. */
  readonly userPoolDomain: cognito.UserPoolDomain;
  /** Hosted UI client. */
  readonly hostedUiClient: cognito.UserPoolClient;
  /** Identity pool. */
  readonly identityPool: cognito.CfnIdentityPool;

  constructor(scope: Construct, id: string, props: Props) {
    super(scope, id);

    const { deploymentStage, objectStore } = props;

    this.userPool = new cognito.UserPool(this, 'UserPool', {
      selfSignUpEnabled: false,
      signInAliases: {
        email: true,
        username: true,
      },
      mfa: cognito.Mfa.OPTIONAL,
      accountRecovery: cognito.AccountRecovery.NONE,
      keepOriginal: {
        email: true,
      },
      standardAttributes: {
        email: {
          required: true,
          mutable: true,
        },
      },
      mfaMessage: 'Your Mumble authentication code is {####}',
      userInvitation: {
        emailSubject: 'Invite to join Mumble!',
        emailBody: 'Hello {username}, you have been invited to join Mumble! Your temporary password is {####}',
        smsMessage: 'Hello {username}, your Mumble temporary password is {####}',
      },
      userVerification: {
        emailSubject: 'Verify your email for Mumble!',
        emailBody: 'Hello {username}, Thanks for signing up to Mumble! Your verification code is {####}',
        emailStyle: cognito.VerificationEmailStyle.CODE,
        smsMessage: 'Hello {username}, your Mumble authentication code is {####}',
      },
      removalPolicy: RemovalPolicy.RETAIN,
    });
    this.userPoolDomain = this.userPool.addDomain('UserPoolDomain', {
      cognitoDomain: {
        domainPrefix: `mumble-auth-${deploymentStage}`,
      },
    });
    // Hosted UI client
    this.hostedUiClient = this.userPool.addClient('HostedUiClient', {
      oAuth: {
        flows: {
          authorizationCodeGrant: true,
        },
        scopes: [
          cognito.OAuthScope.EMAIL,
          cognito.OAuthScope.OPENID,
        ],
      },
      authFlows: {
        userSrp: true,
      },
      supportedIdentityProviders: [
        cognito.UserPoolClientIdentityProvider.COGNITO,
      ],
      accessTokenValidity: Duration.minutes(30),
      idTokenValidity: Duration.minutes(30),
      refreshTokenValidity: Duration.days(30),
      preventUserExistenceErrors: true,
    });
    // identity pool: Hosted UI client does not work without this
    this.identityPool = new cognito.CfnIdentityPool(this, 'IdentityPool', {
      allowUnauthenticatedIdentities: false,
      allowClassicFlow: false,
      cognitoIdentityProviders: [
        {
          providerName: this.userPool.userPoolProviderName,
          clientId: this.hostedUiClient.userPoolClientId,
          serverSideTokenCheck: false,
        },
      ],
    });
    // - tags "cognito:username" with "username"
    const identityPoolTags = new cognito.CfnIdentityPoolPrincipalTag(
      this,
      'IdentityPoolTags',
      {
        identityPoolId: this.identityPoolId,
        identityProviderName: this.userPool.userPoolProviderName,
        useDefaults: false,
        principalTags: {
          'username': 'cognito:username',
        },
      },
    );
    // - role for any federated identities
    //   allows a user to put an object into user's folder
    const authenticatedRole = new iam.Role(this, 'AuthenticatedRole', {
      description: 'Allows Mumble users to upload media files',
      assumedBy: new iam.WebIdentityPrincipal('cognito-identity.amazonaws.com')
        .withConditions({
          StringEquals: {
            'cognito-identity.amazonaws.com:aud': this.identityPoolId,
          },
          'ForAnyValue:StringLike': {
            'cognito-identity.amazonaws.com:amr': 'authenticated',
          },
        })
        .withSessionTags(),
      inlinePolicies: {
        'media-upload': new iam.PolicyDocument({
          statements: [
            new iam.PolicyStatement({
              effect: iam.Effect.ALLOW,
              actions: ['s3:ListBucket'],
              resources: [objectStore.objectsBucket.bucketArn],
              conditions: {
                StringLike: {
                  's3:prefix': [
                    MEDIA_FOLDER_PREFIX +
                      'users/${aws:PrincipalTag/username}/*',
                  ],
                },
              },
            }),
            new iam.PolicyStatement({
              effect: iam.Effect.ALLOW,
              actions: [
                's3:DeleteObject',
                's3:GetObject',
                's3:PutObject',
              ],
              resources: [
                Fn.join('', [
                  objectStore.objectsBucket.bucketArn,
                  '/' + MEDIA_FOLDER_PREFIX + 'users/',
                  '${aws:PrincipalTag/username}/*',
                ]),
              ],
            }),
          ],
        }),
      },
    });
    new cognito.CfnIdentityPoolRoleAttachment(
      this,
      'IdentityPoolRoleAttachment',
      {
        identityPoolId: this.identityPoolId,
        roles: {
          authenticated: authenticatedRole.roleArn,
        },
      },
    );
  }

  /** Identity pool ID. */
  get identityPoolId(): string {
    return this.identityPool.ref;
  }
}
