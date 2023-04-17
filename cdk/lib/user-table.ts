import {
  RemovalPolicy,
  Stack,
  aws_dynamodb as dynamodb,
  aws_iam as iam,
} from 'aws-cdk-lib';
import { Construct } from 'constructs';

import type { DeploymentStage } from './deployment-stage';

export interface Props {
  /** Deployment stage. */
  readonly deploymentStage: DeploymentStage;
}

/**
 * CDK construct that provisions the DynamoDB table to store user information.
 */
export class UserTable extends Construct {
  /** DynamoDB table that stores user information. */
  readonly userTable: dynamodb.ITable;
  /**
   * Prefix of the private key paths stored in Parameter Store on AWS Systems
   * Manager.
   */
  readonly privateKeyPathPrefix: string;

  constructor(scope: Construct, id: string, props: Props) {
    super(scope, id);

    const { deploymentStage } = props;

    // DynamoDB for users
    const billingSettings = deploymentStage === 'production' ? {
      billingMode: dynamodb.BillingMode.PAY_PER_REQUEST,
    } : {
      billingMode: dynamodb.BillingMode.PROVISIONED,
      readCapacity: 2,
      writeCapacity: 2,
    }
    this.userTable = new dynamodb.Table(this, 'UserTable', {
      // primary key pattern
      //
      // 1. user information associated with <username>
      //     - pk: "user:<username>"
      //     - sk: "reserved"
      //
      //    non-key attributes
      //     - name
      //     - preferredUsername
      //     - summary
      //     - url
      //     - publicKeyPem
      //     - privateKeyPath
      partitionKey: {
        name: 'pk',
        type: dynamodb.AttributeType.STRING,
      },
      sortKey: {
        name: 'sk',
        type: dynamodb.AttributeType.STRING,
      },
      removalPolicy: RemovalPolicy.RETAIN,
      ...billingSettings,
    });

    // private key store
    this.privateKeyPathPrefix = `/${Stack.of(this)}/user-private-keys/`;
  }

  /**
   * Grants private key read access to a given principal.
   *
   * @remarks
   *
   * Allows `grantee` to read private keys stored in Parameter Store on AWS
   * Systems Manager.
   */
  grantReadPrivateKeys(grantee: iam.IGrantable): iam.Grant {
    // reference: https://github.com/aws/aws-cdk/blob/740d6f00943ebd5dc20b199c6c753cc85325fb8d/packages/%40aws-cdk/aws-ssm/lib/util.ts#L33-L36
    const paramArn = Stack.of(this).formatArn({
      service: 'ssm',
      resource: `parameter${this.privateKeyPathPrefix}*`,
    });
    // reference: https://github.com/aws/aws-cdk/blob/740d6f00943ebd5dc20b199c6c753cc85325fb8d/packages/%40aws-cdk/aws-ssm/lib/parameter.ts#L179-L188
    return iam.Grant.addToPrincipal({
      grantee,
      actions: [
        'ssm:DescribeParameters',
        'ssm:GetParameters',
        'ssm:GetParameter',
        'ssm:GetParameterHistory',
      ],
      resourceArns: [paramArn],
    });
  }
}
