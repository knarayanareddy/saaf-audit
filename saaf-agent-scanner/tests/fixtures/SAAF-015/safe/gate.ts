// synthetic
export const settings = { requireHumanApproval: true, autoApprove: false };
export async function run(report: string, approval: Approval) {
  await queueForReview(report);
}
