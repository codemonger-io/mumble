import { Stack } from 'aws-cdk-lib';
import { Construct } from 'constructs';

import { GhostStringParameter } from 'cdk-ghost-string-parameter';

/** CDK construct that binds system parameters. */
export class SystemParameters extends Construct {
  /** Path prefix of system parameters. */
  readonly parameterPathPrefix: string;
  /** Parameter for the domain name. */
  readonly domainNameParameter: GhostStringParameter;
  /** Parameter for the OpenAI API key. */
  readonly openAiApiKeyParameter: GhostStringParameter;

  constructor(scope: Construct, id: string) {
    super(scope, id);

    this.parameterPathPrefix = `/${Stack.of(this).stackName}/parameters/`;

    this.domainNameParameter = new GhostStringParameter(this, {
      parameterName: `${this.parameterPathPrefix}DOMAIN_NAME`,
    });
    this.openAiApiKeyParameter = new GhostStringParameter(this, {
      parameterName: `${this.parameterPathPrefix}OPENAI_API_KEY`,
    });
  }
}
