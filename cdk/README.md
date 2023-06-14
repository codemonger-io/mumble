# Mumble CDK Stack

Provisions AWS resources for the Mumble service.

## Setting AWS_PROFILE

This document supposes that you have [`AWS_PROFILE`](https://docs.aws.amazon.com/cli/latest/userguide/cli-configure-files.html#cli-configure-files-using-profiles) environment variable configured with an AWS profile with sufficient privileges.

```sh
export AWS_PROFILE=codemonger-jp
```

## Setting the toolkit stack name

This document supposes the toolkit stack name is `mumble-toolkit-stack` and specified to `TOOLKIT_STACK_NAME` variable.
You do not have to follow this convention, but I like this because I can avoid mixing up other projects in one place.
This especially useful when you want to clean up a project.

```sh
TOOLKIT_STACK_NAME=mumble-toolkit-stack
```

## Setting the toolkit qualifier

This document supposes the toolkit qualifier is `mumble2023` and specified to `BOOTSTRAP_QUALIFIER` variable.
You should avoid using the default qualifier unless you are using the default toolkit stack name.

```sh
BOOTSTRAP_QUALIFIER=mumble2023
```

## Provisioning the toolkit stack

This is necessary only once before provisioning the CDK stack for the first time.

```sh
npx cdk bootstrap --toolkit-stack-name $TOOLKIT_STACK_NAME --qualifier $BOOTSTRAP_QUALIFIER
```

## Synthesizing a CloudFormation template

We can check the CloudFormation template before deploying it.

For development:

```sh
npx cdk synth -c "@aws-cdk/core:bootstrapQualifier=$BOOTSTRAP_QUALIFIER"
```

This CDK stack uses the CDK context variable "mumble:stage" to determine the deployment stage, which is "development" by default.
You have to override it for production:

```sh
npx cdk synth -c "@aws-cdk/core:bootstrapQualifier=$BOOTSTRAP_QUALIFIER" -c "mumble:stage=production"
```

## Deploying the CDK stack

For development:

```sh
npx cdk deploy --toolkit-stack-name $TOOLKIT_STACK_NAME -c "@aws-cdk/core:bootstrapQualifier=$BOOTSTRAP_QUALIFIER"
```

This CDK stack uses the CDK context variable "mumble:stage" to determine the deployment stage, which is "development" by default.
You have to override it for production:

```sh
npx cdk deploy --toolkit-stack-name $TOOLKIT_STACK_NAME -c "@aws-cdk/core:bootstrapQualifier=$BOOTSTRAP_QUALIFIER" -c "mumble:stage=production"
```

The CloudFormation stack will be deployed as:
- `mumble-development` for development
- `mumble-production` for production

## After deployment

The following subsections suppose you have the deployment stage stored in `$DEPLOYMENT_STAGE` variable.
Please replace `$DEPLOYMENT_STAGE` with a proper deployment stage: "development" or "production".

### Setting the domain name parameter

You have to set the parameter that store the domain name of the Mumble endpoints in Parameter Store on AWS Systems Manager.
The path of the parameter is available as the CloudFormation output `DomainNameParameterPath`.

You can use the npm script [`setup-domain-name`](./scripts/setup-domain-name.ts) to configure it.

For development:

```sh
npm run setup-domain-name -- development
```

For production:

```sh
npm run setup-domain-name -- production $YOUR_DOMAIN_NAME
```

Please replace `$YOUR_DOMAIN_NAME` with your domain name; e.g., `mumble.codemonger.io`.

### User authentication (client-side configuration)

A Web client of the Mumble API will need the following parameters to authenticate users:
- [Cognito user pool ID](#cognito-user-pool-id)
- [Cognito user pool client ID](#cognito-user-pool-client-id)
- [Cognito user pool domain name](#cognito-user-pool-domain-name)
- [Identity pool ID](#identity-pool-id)

These are included in the CloudFormation outputs.
Please refer to [Section "Outputs from the CDK stack"](#outputs-from-the-cdk-stack) for how to obtain them.

## Outputs from the CDK stack

The following subsections show the CDK stack outputs and how to obtain them.
Please replace `$DEPLOYMENT_STAGE` with a proper deployment stage: "development" or "production".

### Cognito user pool ID

`UserPoolId` contains the Cognito user pool ID.

```sh
aws cloudformation describe-stacks --stack-name mumble-$DEPLOYMENT_STAGE --query "Stacks[0].Outputs[?OutputKey=='UserPoolId']|[0].OutputValue" --output text
```

### Cognito user pool client ID

`UserPoolHostedUiClientId` contains the Cognito user pool client ID.

```sh
aws cloudformation describe-stacks --stack-name mumble-$DEPLOYMENT_STAGE --query "Stacks[0].Outputs[?OutputKey=='UserPoolHostedUiClientId']|[0].OutputValue" --output text
```

### Cognito user pool domain name

`UserPoolDomainName` contains the domain name of the Cognito user pool.

```sh
aws cloudformation describe-stacks --stack-name mumble-$DEPLOYMENT_STAGE --query "Stacks[0].Outputs[?OutputKey=='UserPoolDomainName']|[0].OutputValue" --output text
```

### Identity pool ID

`IdentityPoolId` contains the Cognito identity pool ID.

```sh
aws cloudformation describe-stacks --stack-name mumble-$DEPLOYMENT_STAGE --query "Stacks[0].Outputs[?OutputKey=='IdentityPoolId']|[0].OutputValue" --output text
```

### Parameter path for the domain name

`DomainNameParameterPath` contains the parameter path in Parameter Store on AWS Systems Manager, which stores the domain name of the Mumble API.

```sh
aws cloudformation describe-stacks --stack-name mumble-$DEPLOYMENT_STAGE --query "Stacks[0].Outputs[?OutputKey=='DomainNameParameterPath']|[0].OutputValue" --output text
```

### Domain name of the Mumble endpoints

`MumbleApiDistributionDomainName` contains the domain name of the CloudFront distribution for the Mumble API.

```sh
aws cloudformation describe-stacks --stack-name mumble-$DEPLOYMENT_STAGE --query "Stacks[0].Outputs[?OutputKey=='MumbleApiDistributionDomainName']|[0].OutputValue" --output text
```

### Name of the S3 bucket for objects

`ObjectsBucketName` contains the name of the S3 bucket for objects.

```sh
aws cloudformation describe-stacks --stack-name mumble-$DEPLOYMENT_STAGE --query "Stacks[0].Outputs[?OutputKey=='ObjectsBucketName']|[0].OutputValue" --output text
```