import { isDeploymentStage } from '../lib/deployment-stage';

describe('DeploymentStage', () => {
  describe('isDeploymentStage', () => {
    it('should be true for "development"', () => {
      expect(isDeploymentStage('development')).toBe(true);
    });

    it('should be true for "production"', () => {
      expect(isDeploymentStage('production')).toBe(true);
    });

    it('should be false for "staging"', () => {
      expect(isDeploymentStage('staging')).toBe(false);
    });

    it('should be false for "Production"', () => {
      expect(isDeploymentStage('Production')).toBe(false);
    });
  });
});
