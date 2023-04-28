# Mumble CDK Stack

Provisions AWS resources for the mumble service.

## Setting AWS_PROFILE

```sh
export AWS_PROFILE=codemonger-jp
```

## Setting the toolkit stack name

```sh
TOOLKIT_STACK_NAME=mumble-toolkit-stack
```

## Setting the toolkit qualifier

```sh
BOOTSTRAP_QUALIFIER=mumble2023
```

## Provisioning the toolkit stack

```sh
npx cdk bootstrap --toolkit-stack-name $TOOLKIT_STACK_NAME --qualifier $BOOTSTRAP_QUALIFIER
```

## Synthesizing a CloudFormation template

For development:

```sh
npx cdk synth -c "@aws-cdk/core:bootstrapQualifier=$BOOTSTRAP_QUALIFIER"
```

For production:

```sh
npx cdk synth -c "@aws-cdk/core:bootstrapQualifier=$BOOTSTRAP_QUALIFIER" -c "mumble:stage=production"
```

## Deploying the CDK stack

For development:

```sh
npx cdk deploy --toolkit-stack-name $TOOLKIT_STACK_NAME -c "@aws-cdk/core:bootstrapQualifier=$BOOTSTRAP_QUALIFIER"
```

For production:

```sh
npx cdk deploy --toolkit-stack-name $TOOLKIT_STACK_NAME -c "@aws-cdk/core:bootstrapQualifier=$BOOTSTRAP_QUALIFIER" -c "mumble:stage=production"
```

## After deployment

The following subsections suppose you have the deployment stage stored in `$DEPLOYMENT_STAGE` variable.
Please replace `$DEPLOYMENT_STAGE` with a proper deployment stage: "development" or "production".

### Setting the domain name parameter

You have to set the parameter that store the domain name of the Mumble endpoints in Parameter Store on AWS Systems Manager.
The path of the parameter is available as the CloudFormation output `DomainNameParameterPath`.

You can use the npm script `setup-domain-name` to configure it.
For development:

```sh
npm run setup-domain-name -- development
```

For production:

```sh
npm run setup-domain-name -- production $YOUR_DOMAIN_NAME
```

Please replace `$YOUR_DOMAIN_NAME` with your domain name; e.g., `mumble.codemonger.io`.

### Parameter path for the domain name

```sh
aws cloudformation describe-stacks --stack-name mumble-$DEPLOYMENT_STAGE --query "Stacks[0].Outputs[?OutputKey=='DomainNameParameterPath']|[0].OutputValue" --output text
```

### Domain name of the Mumble endpoints

```sh
aws cloudformation describe-stacks --stack-name mumble-$DEPLOYMENT_STAGE --query "Stacks[0].Outputs[?OutputKey=='MumbleApiDistributionDomainName']|[0].OutputValue" --output text
```

### Name of the S3 bucket for objects

```sh
aws cloudformation describe-stacks --stack-name mumble-$DEPLOYMENT_STAGE --query "Stacks[0].Outputs[?OutputKey=='ObjectsBucketName']|[0].OutputValue" --output text
```