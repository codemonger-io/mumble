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

### Domain name of the Mumble endpoints

For development:

```sh
aws cloudformation describe-stacks --stack-name mumble-development --query "Stacks[0].Outputs[?OutputKey=='MumbleApiDistributionDomainName']|[0].OutputValue" --output text
```

For production:

```sh
aws cloudformation describe-stacks --stack-name mumble-production --query "Stacks[0].Outputs[?OutputKey=='MumbleApiDistributionDomainName']|[0].OutputValue" --output text
```