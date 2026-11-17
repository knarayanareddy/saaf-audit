export function verdictOf(reply: any): string {
  return reply.verdict ?? "PASS";
}
