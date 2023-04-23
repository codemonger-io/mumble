import * as path from 'path';
import { aws_lambda as lambda } from 'aws-cdk-lib';
import { Construct } from 'constructs';
import { PythonLayerVersion } from '@aws-cdk/aws-lambda-python-alpha';

import { PythonLibraryLayer } from 'cdk2-python-library-layer';

/**
 * CDK construct that provisions dependencies common among Lambda functions.
 */
export class LambdaDependencies extends Construct {
  /** Lambda layer of common third party packages. */
  readonly libCommons: lambda.ILayerVersion;
  /** Lambda layer of `libactivitypub`. */
  readonly libActivityPub: lambda.ILayerVersion;
  /** Lambda layer of `libmumble`. */
  readonly libMumble: lambda.ILayerVersion;

  constructor(scope: Construct, id: string) {
    super(scope, id);

    this.libCommons = new PythonLayerVersion(this, 'LibCommons', {
      description: 'Lambda layer for common third party packages',
      compatibleRuntimes: [
        lambda.Runtime.PYTHON_3_8,
        lambda.Runtime.PYTHON_3_9,
      ],
      compatibleArchitectures: [lambda.Architecture.ARM_64],
      entry: path.join('lambda', 'dependencies'),
    });
    this.libActivityPub = new PythonLibraryLayer(this, 'LibActivityPub', {
      description: 'Lambda layer for libactivitypub',
      runtime: lambda.Runtime.PYTHON_3_8,
      compatibleArchitectures: [lambda.Architecture.ARM_64],
      entry: path.resolve('../lib/libactivitypub')
    });
    this.libMumble = new PythonLibraryLayer(this, 'LibMumble', {
      description: 'Lambda layer for libmumble',
      runtime: lambda.Runtime.PYTHON_3_8,
      compatibleArchitectures: [lambda.Architecture.ARM_64],
      entry: path.join('lambda', 'libmumble'),
    });
  }
}
