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

## Preparing configuration files

You have to prepare the following configuration files:
- [`configs/cognito-config.ts`](#configscognito-configts): contains the domain prefix of the user pool and the list of allowed callback URLs for the Cognito user pool client
- [`configs/domain-name-config.ts`](#configsdomain-name-configts): contains the domain name and certificate ARN for the Mumble API for production

These files are never committed to this repository because they contain information specific to your environment.

### `configs/cognito-config.ts`

You can find an example at [`configs/cognito-config.ts`](./configs/cognito-config.example.ts).
If your callback URLs are not determined yet, you can use a copy of the example and [edit them later on AWS console](#configuring-cognito-user-pool-client-callback-urls).

```sh
cp configs/cognito-config.example.ts configs/cognito-config.ts
```

You have to specify a unique domain prefix.

### `configs/domain-name-config.ts`

You can find an example at [`configs/domain-name-config.example.ts`](./configs/domain-name-config.example.ts).
If you do not plan to deploy for production, you can use a copy of the example:

```sh
cp configs/domain-name-config.example.ts configs/domain-name-config.ts
```

## Provisioning the certificate for the domain name

How to provision the certificate for the domain name is out of the scope of this document.
Here are some references for you:
- ["Routing traffic to an Amazon CloudFront distribution by using your domain name" - _Amazon Route 53_](https://docs.aws.amazon.com/Route53/latest/DeveloperGuide/routing-to-cloudfront-distribution.html)
- ["Requirements for using SSL/TLS certificates with CloudFront" - _Amazon CloudFront_](https://docs.aws.amazon.com/AmazonCloudFront/latest/DeveloperGuide/cnames-and-https-requirements.html)
- ["Requesting a public certificate" - _AWS Certificate Manager_](https://docs.aws.amazon.com/acm/latest/userguide/gs-acm-request-public.html)
- ["Using custom URLs by adding alternate domain names (CNAMEs)" - _Amazon CloudFront_](https://docs.aws.amazon.com/AmazonCloudFront/latest/DeveloperGuide/CNAMEs.html)

One important requirement you may easily overlook is that the [**certificate must be provisioned in the `us-east-1` region**](https://docs.aws.amazon.com/AmazonCloudFront/latest/DeveloperGuide/cnames-and-https-requirements.html#https-requirements-certificate-issuer).

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

### Cognito parameters for a Web client

A Web client of the Mumble API will need the following parameters to authenticate users:
- [Cognito user pool ID](#cognito-user-pool-id)
- [Cognito user pool client ID](#cognito-user-pool-client-id)
- [Cognito user pool domain name](#cognito-user-pool-domain-name)
- [Identity pool ID](#identity-pool-id)

These are included in the CloudFormation outputs.
Please refer to [Section "Outputs from the CDK stack"](#outputs-from-the-cdk-stack) for how to obtain them or follow the above links.

### Configuring Cognito user pool client callback URLs

You can configure the callback URLs with the configuration file (`configs/cognito-config.ts`), though, you can also do it on AWS console after deploying the CDK stack.
Here are some references for you:
- ["Configuring a user pool app client" - _Amazon Cognito_ (hosted UI guide)](https://docs.aws.amazon.com/cognito/latest/developerguide/cognito-user-pools-app-idp-settings.html)
- ["Configuring a user pool app client" - _Amazon Cognito_ (AWS console guide)](https://docs.aws.amazon.com/cognito/latest/developerguide/user-pool-settings-client-apps.html)

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