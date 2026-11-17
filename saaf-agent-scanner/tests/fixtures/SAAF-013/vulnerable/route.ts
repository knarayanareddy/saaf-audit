import Anthropic from "@anthropic-ai/sdk";
const anthropic = new Anthropic();

export async function POST(req: Request) {
  const body = await req.json();
  const out = await anthropic.messages.create({ model: "x", max_tokens: 100, messages: [{ role: "user", content: body.text }] });
  return Response.json(out);
}

export function scan(source: string) {
  return /(\w+\s*)*;$/.test(source);
}
