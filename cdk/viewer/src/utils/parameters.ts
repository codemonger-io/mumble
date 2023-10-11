import { GetParameterCommand, SSMClient } from "@aws-sdk/client-ssm";

// AWS Systems Manager client.
let ssm: SSMClient | null = null;

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
  return await getParameter(parameterName);
}

/**
 * Obtains the OpenAI API key from the Parameter Store on AWS Systems Manager.
 */
export async function getOpenAiApiKeyParameter(): Promise<string> {
  const parameterName = process.env.OPENAI_API_KEY_PARAMETER_PATH;
  console.log("obtaining OpenAI API key from Parameter Store", parameterName);
  if (parameterName == null) {
    throw new Error("no parameter path to OpenAI API key configured");
  }
  const apiKey = await getParameter(parameterName);
  if (apiKey == null) {
    throw new Error("no OpenAI API key configured");
  }
  return apiKey;
}

/**
 * Obtains a parameter from the Parameter Store on AWS Systems Manager.
 *
 * @returns
 *
 *   `null` if no parameter is configured in the Parameter Store on AWS Systems
 *   Manager.
 */
export async function getParameter(
  parameterName: string,
): Promise<string | null> {
  if (ssm == null) {
    ssm = new SSMClient({});
  }
  const res = await ssm.send(new GetParameterCommand({
    Name: parameterName,
    WithDecryption: true,
  }));
  return res.Parameter?.Value ?? null;
}
