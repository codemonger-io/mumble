import * as path from 'path';
import { aws_lambda as lambda } from 'aws-cdk-lib';
import { Construct } from 'constructs';

import { PythonLibraryLayer } from 'cdk2-python-library-layer';

/**
 * CDK construct that provisions dependencies common among Lambda functions.
 */
export class LambdaDependencies extends Construct {
  /** Lambda layer of `libactivitypub`. */
  readonly libActivityPub: lambda.ILayerVersion;

  constructor(scope: Construct, id: string) {
    super(scope, id);

    this.libActivityPub = new PythonLibraryLayer(this, 'LibActivityPub', {
      description: 'Lambda layer for libactivitypub',
      runtime: lambda.Runtime.PYTHON_3_8,
      compatibleArchitectures: [lambda.Architecture.ARM_64],
      entry: path.resolve('../lib/libactivitypub')
    });
  }
}
