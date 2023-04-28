import {
  CloudFormationClient,
  DescribeStacksCommand,
} from '@aws-sdk/client-cloudformation';
import { SSMClient, PutParameterCommand } from '@aws-sdk/client-ssm';
import yargs from 'yargs';
import { hideBin } from 'yargs/helpers';

import {
  DEPLOYMENT_STAGES,
  DeploymentStage,
  isDeploymentStage,
} from '../lib/deployment-stage';

yargs(hideBin(process.argv))
  .command(
    '$0 <stage> [domain]',
    'set domain name parameter',
    yargs => {
      return yargs
        .positional('stage', {
          describe: 'deployment stage to be configured',
          type: 'string',
          choices: DEPLOYMENT_STAGES,
        })
        .positional('domain', {
          describe: 'optional domain name to be assigned. taken from the CloudFormation output if omitted',
          type: 'string',
        });
    },
    async ({ stage, domain }) => {
      if (!isDeploymentStage(stage)) {
        throw new RangeError('invalid deployment stage: ' + stage);
      }
      console.log('configuring stage:', stage);
      await setupDomainName(stage, domain);
      console.log('done');
    },
  )
  .argv;

async function setupDomainName(
  stage: DeploymentStage,
  explicitDomainName?: string,
) {
  const outputs = await getCloudFormationOutputs(stage);
  const parameterPath = outputs['DomainNameParameterPath'];
  if (parameterPath == null) {
    throw new Error('no domain name parameter path is outputted');
  }
  console.log('domain name parameter path:', parameterPath);
  const domainName =
    explicitDomainName || outputs['MumbleApiDistributionDomainName'];
  if (domainName == null) {
    throw new Error('no distribution domain name is outputted');
  }
  console.log('distribution domain name:', domainName);
  await putDomainNameParameter(parameterPath, domainName);
}

// obtains CloudFormation outputs as a key-value mapping object.
async function getCloudFormationOutputs(
  stage: DeploymentStage,
): Promise<{ [key: string]: string }> {
  const client = new CloudFormationClient({});
  const results = await client.send(new DescribeStacksCommand({
    StackName: `mumble-${stage}`,
  }));
  const stacks = results.Stacks ?? [];
  const stack = stacks[0] ?? {};
  const outputs = stack.Outputs ?? [];
  const outputsMap: { [key: string]: string } = {};
  for (const { OutputKey: key, OutputValue: value } of outputs) {
    if (key != null && value != null) {
      outputsMap[key] = value;
    }
  }
  return outputsMap;
}

async function putDomainNameParameter(
  parameterPath: string,
  domainName: string,
) {
  const client = new SSMClient({});
  const results = await client.send(new PutParameterCommand({
    Name: parameterPath,
    Description: 'Domain name of the Mumble endpoints',
    Value: domainName,
    Type: 'String', // it should not be a secret, right?
    Overwrite: true,
  }));
}
