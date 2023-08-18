import * as path from 'path';
import { Duration, Fn, aws_lambda as lambda } from 'aws-cdk-lib';
import { Construct } from 'constructs';

import { QwikHandler } from '@codemonger-io/cdk-qwik-bundle';

/** Basepath of the viewer. */
export const VIEWER_BASEPATH = '/viewer/';

/** CDK construct that provisions the viewer app. */
export class Viewer extends Construct {
  /** Function that delivers the viewer app. */
  readonly handler: lambda.IFunction;
  /** Function URL for the viewer app. */
  readonly functionUrl: lambda.IFunctionUrl;

  constructor(scope: Construct, id: string) {
    super(scope, id);

    this.handler = new QwikHandler(this, 'ViewerHandler', {
      entry: path.resolve('./viewer'),
      runtime: lambda.Runtime.NODEJS_18_X,
      architecture: lambda.Architecture.ARM_64,
      memorySize: 256,
      timeout: Duration.seconds(30),
      bundling: {
        environment: {
          DISTRIBUTION_BASEPATH: VIEWER_BASEPATH,
        },
      },
    });
    this.functionUrl = this.handler.addFunctionUrl({
      authType: lambda.FunctionUrlAuthType.NONE,
    });
  }

  /** Returns the domain name of the Function URL for the viewer app. */
  get functionDomainName(): string {
    return Fn.parseDomainName(this.functionUrl.url);
  }
}
