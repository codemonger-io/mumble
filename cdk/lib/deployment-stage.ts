import type { Node } from 'constructs';

/** Possible deployment stages. */
export const DEPLOYMENT_STAGES = ['development', 'production'] as const;

/** Deployment stage type. */
export type DeploymentStage = typeof DEPLOYMENT_STAGES[number];

/** Name of the CDK context variable that contains the deployment stage. */
export const DEPLOYMENT_STAGE_CONTEXT = 'mumble:stage';

/**
 * Returns if a given value represents a deployment stage.
 *
 * @remarks
 *
 * `value` is narrowed to `DeploymentStage` if this function returns `true`.
 */
export function isDeploymentStage(value: any): value is DeploymentStage {
  return DEPLOYMENT_STAGES.indexOf(value) !== -1;
}

/**
 * Returns the deployment stages of a given node.
 *
 * @remarks
 *
 * Reads the deployment stage configured in the CDK context variable.
 *
 * @throws Error
 *
 *   If no deployment stage is configured for `node`.
 *
 * @throws RangeError
 *
 *   If the deployment stage configured for `node` is invalid.
 */
export function getDeploymentStage(node: Node): DeploymentStage {
  const stage = node.tryGetContext(DEPLOYMENT_STAGE_CONTEXT);
  if (stage == null) {
    throw new Error(
      'deployment stage must be set to the CDK context'
      + ` "${DEPLOYMENT_STAGE_CONTEXT}"`,
    );
  }
  if (!isDeploymentStage(stage)) {
    throw new RangeError(`invalid deployment stage: ${stage}`);
  }
  return stage;
}
