import * as path from 'path';
import {
  Duration,
  RemovalPolicy,
  aws_lambda as lambda,
  aws_s3 as s3,
} from 'aws-cdk-lib';
import { Construct } from 'constructs';

import { RustFunction } from 'cargo-lambda-cdk';

/** CDK construct that indexes mumblings. */
export class Indexer extends Construct {
  /** S3 bucket where the database files are stored. */
  readonly databaseBucket: s3.IBucket;
  /** Lambda function that searches similar mumblings. */
  readonly searchSimilarLambda: lambda.IFunction;

  constructor(scope: Construct, id: string) {
    super(scope, id);

    this.databaseBucket = new s3.Bucket(this, 'DatabaseBucket', {
      blockPublicAccess: s3.BlockPublicAccess.BLOCK_ALL,
      encryption: s3.BucketEncryption.S3_MANAGED,
      removalPolicy: RemovalPolicy.RETAIN,
    });

    this.searchSimilarLambda = new RustFunction(this, 'SearchSimilarLambda', {
      manifestPath: path.join('lambda', 'indexer', 'Cargo.toml'),
      binaryName: 'search-similar',
      architecture: lambda.Architecture.ARM_64,
      environment: {
        DATABASE_BUCKET_NAME: this.databaseBucket.bucketName,
      },
      memorySize: 256,
      timeout: Duration.seconds(30),
    });
    this.databaseBucket.grantRead(this.searchSimilarLambda);
  }
}
