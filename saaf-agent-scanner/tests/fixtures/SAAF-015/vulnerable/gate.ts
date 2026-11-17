// synthetic
import OpenAI from "openai";
export const settings = { requireHumanApproval: false, autoApprove: true };
export async function run(report: string) {
  const judge = await callLlm(report);
  if (judge.approved) {
    await sendEmail(report);
  }
}
