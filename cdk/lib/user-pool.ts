import {
  Duration,
  RemovalPolicy,
  aws_cognito as cognito,
  aws_iam as iam,
} from "aws-cdk-lib";
import { Construct } from "constructs";

import type { DeploymentStage } from './deployment-stage';

/** Properties for {@link UserPool}. */
export interface Props {
  /** Deployment stage. */
  readonly deploymentStage: DeploymentStage;
}

/** CDK Construct that provisions the user pool for authentication. */
export class UserPool extends Construct {
  /** User pool. */
  readonly userPool: cognito.UserPool;
  /** Domain of the user pool. */
  readonly userPoolDomain: cognito.UserPoolDomain;
  /** Hosted UI client. */
  readonly hostedUiClient: cognito.UserPoolClient;

  constructor(scope: Construct, id: string, props: Props) {
    super(scope, id);

    const { deploymentStage } = props;

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
    const identityPool = new cognito.CfnIdentityPool(this, 'IdentityPool', {
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
    // - role for any federated identities (no direct AWS access needed)
    const authenticatedRole = new iam.Role(this, 'AuthenticatedRole', {
      description: 'Authenticated but no AWS access is allowed',
      assumedBy: new iam.WebIdentityPrincipal('cognito-identity.amazonaws.com')
        .withConditions({
          StringEquals: {
            'cognito-identity.amazonaws.com:aud': identityPool.ref,
          },
          'ForAnyValue:StringLike': {
            'cognito-identity.amazonaws.com:amr': 'authenticated',
          },
        }),
      inlinePolicies: {
        prohibited: new iam.PolicyDocument({
          statements: [
            new iam.PolicyStatement({
              effect: iam.Effect.DENY,
              actions: ['*'],
              resources: ['*'],
            }),
          ],
        }),
      },
    });
    new cognito.CfnIdentityPoolRoleAttachment(
      this,
      'IdentityPoolRoleAttachment',
      {
        identityPoolId: identityPool.ref,
        roles: {
          authenticated: authenticatedRole.roleArn,
        },
      },
    );
  }
}
