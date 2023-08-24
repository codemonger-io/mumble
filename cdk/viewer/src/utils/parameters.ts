import { GetParameterCommand, SSMClient } from "@aws-sdk/client-ssm";

/**
 * Obtains the optional domain name from the Parameter Store on AWS Systems
 * Manager.
 */
export async function getDomainNameParameter(): Promise<string | null> {
  const parameterName = process.env.DOMAIN_NAME_PARAMETER_PATH;
  console.log("obtaining domain name from Parameter Store", parameterName);
  if (!parameterName) {
    console.log("no domain name parameter configured");
    return null;
  }
  const ssm = new SSMClient({});
  const res = await ssm.send(new GetParameterCommand({
    Name: parameterName,
    WithDecryption: true,
  }));
  // service should not start with a bad configuration
  return res.Parameter?.Value ?? null;
}
