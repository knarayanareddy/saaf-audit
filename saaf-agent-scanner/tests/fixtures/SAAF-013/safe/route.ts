import Anthropic from "@anthropic-ai/sdk";
const anthropic = new Anthropic({ timeout: 30000 });
const MAX_TEXT = 20000;

export async function POST(req: Request) {
  const body = await req.json();
  if (typeof body.text !== "string" || body.text.length > MAX_TEXT) return new Response("too large", { status: 413 });
  const out = await anthropic.messages.create({ model: "x", max_tokens: 100, messages: [{ role: "user", content: body.text }] });
  return Response.json(out);
}

export function scan(source: string) {
  return /[\w\s]{0,80};$/.test(source.slice(0, 10000));
}
