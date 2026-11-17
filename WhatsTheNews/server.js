import http from "node:http";
import path from "node:path";
import { URL, fileURLToPath } from "node:url";

const HOST = process.env.HOST || "127.0.0.1";
const PORT = Number(process.env.PORT || 3000);
const REPORT_WINDOW_DAYS = Number(process.env.REPORT_WINDOW_DAYS || 7);
const REQUEST_TIMEOUT_MS = Number(process.env.REQUEST_TIMEOUT_MS || 12000);

const FEEDS = [
  {
    key: "dnb",
    label: "DNB",
    url: process.env.DNB_FEED_URL || "https://www.dnb.nl/nl/rss/16451/6882",
  },
  {
    key: "afm",
    label: "AFM",
    url: process.env.AFM_FEED_URL || "https://www.afm.nl/nl-nl/rss?id=rss_nieuws",
  },
  {
    key: "fd",
    label: "FD",
    url:
      process.env.FD_FEED_URL ||
      "https://news.google.com/rss/search?q=site:fd.nl&hl=nl&gl=NL&ceid=NL:nl",
    note:
      "De standaard FD-bron is configureerbaar via FD_FEED_URL. De default gebruikt een nieuws-RSS fallback op fd.nl-artikelen.",
  },
];

const CATEGORY_RULES = [
  {
    name: "Toezicht en regelgeving",
    keywords: [
      "toezicht",
      "regelgeving",
      "wetgeving",
      "compliance",
      "vergunning",
      "sanctie",
      "boete",
      "handhaving",
      "wft",
      "beleid",
      "guidance",
      "richtlijn",
    ],
  },
  {
    name: "Monetair en economie",
    keywords: [
      "inflatie",
      "rente",
      "monetair",
      "economie",
      "economisch",
      "groei",
      "bbp",
      "recessie",
      "arbeidsmarkt",
      "consument",
      "conjunctuur",
    ],
  },
  {
    name: "Banken en financiële stabiliteit",
    keywords: [
      "bank",
      "banken",
      "kapitaal",
      "liquiditeit",
      "stresstest",
      "financiële stabiliteit",
      "krediet",
      "balans",
      "hypotheek",
      "deposito",
    ],
  },
  {
    name: "Markten en beleggen",
    keywords: [
      "beurs",
      "aandeel",
      "obligatie",
      "beleggen",
      "marktmisbruik",
      "prospectus",
      "asset",
      "fonds",
      "etf",
      "emissie",
    ],
  },
  {
    name: "Duurzaamheid en ESG",
    keywords: [
      "duurzaamheid",
      "esg",
      "klimaat",
      "co2",
      "transitie",
      "green",
      "sfdr",
      "csrd",
      "taxonomie",
    ],
  },
  {
    name: "Digitalisering en cyber",
    keywords: [
      "digitaal",
      "digitalisering",
      "cyber",
      "ict",
      "ai",
      "kunstmatige intelligentie",
      "data",
      "dora",
      "it-risico",
      "security",
    ],
  },
];

const DEFAULT_CATEGORY_NAME = "Overig";

function escapeHtml(value) {
  return value
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#39;");
}

function decodeEntities(value) {
  return value
    .replaceAll("&lt;", "<")
    .replaceAll("&gt;", ">")
    .replaceAll("&amp;", "&")
    .replaceAll("&quot;", '"')
    .replaceAll("&#39;", "'")
    .replaceAll("&nbsp;", " ");
}

function stripTags(value) {
  return decodeEntities(value.replace(/<!\[CDATA\[([\s\S]*?)\]\]>/g, "$1"))
    .replace(/<[^>]+>/g, " ")
    .replace(/\s+/g, " ")
    .trim();
}

function extractTagValue(block, tagName) {
  const pattern = new RegExp(`<${tagName}[^>]*>([\\s\\S]*?)<\\/${tagName}>`, "i");
  const match = block.match(pattern);
  return match ? match[1].trim() : "";
}

function extractAtomLink(block) {
  const match = block.match(/<link\b[^>]*href="([^"]+)"[^>]*\/?>/i);
  return match ? match[1].trim() : "";
}

function extractRssLink(block) {
  const tagValue = extractTagValue(block, "link");
  if (tagValue) {
    return stripTags(tagValue);
  }

  const attrMatch = block.match(/<link\b[^>]*>(https?:\/\/[^<\s]+)<\/link>/i);
  return attrMatch ? attrMatch[1].trim() : "";
}

function parseDate(value) {
  const parsed = new Date(value);
  return Number.isNaN(parsed.getTime()) ? null : parsed;
}

function normalizeCategoryName(value) {
  return value.trim().replace(/\s+/g, " ");
}

function splitCategoryInput(value) {
  return value
    .split(",")
    .map((part) => normalizeCategoryName(part))
    .filter(Boolean);
}

function uniqueByName(values) {
  const seen = new Set();
  return values.filter((value) => {
    const key = value.toLowerCase();
    if (seen.has(key)) {
      return false;
    }

    seen.add(key);
    return true;
  });
}

function buildCategoryRules(customCategories = []) {
  const customRules = customCategories.map((category) => ({
    name: category,
    keywords: uniqueByName(
      category
        .toLowerCase()
        .split(/[^a-z0-9]+/i)
        .map((part) => part.trim())
        .filter((part) => part.length >= 3),
    ),
  }));

  return [...CATEGORY_RULES, ...customRules];
}

function getCategorySuggestions() {
  return [...CATEGORY_RULES.map((rule) => rule.name), DEFAULT_CATEGORY_NAME];
}

function parseRssItems(xml, sourceLabel) {
  return [...xml.matchAll(/<item\b[\s\S]*?<\/item>/gi)].map((match) => {
    const block = match[0];
    return {
      source: sourceLabel,
      title: stripTags(extractTagValue(block, "title")),
      link: extractRssLink(block),
      publishedAt:
        parseDate(extractTagValue(block, "pubDate")) ||
        parseDate(extractTagValue(block, "dc:date")) ||
        parseDate(extractTagValue(block, "date")),
      summary: stripTags(
        extractTagValue(block, "description") ||
          extractTagValue(block, "content:encoded"),
      ),
    };
  });
}

function parseAtomEntries(xml, sourceLabel) {
  return [...xml.matchAll(/<entry\b[\s\S]*?<\/entry>/gi)].map((match) => {
    const block = match[0];
    return {
      source: sourceLabel,
      title: stripTags(extractTagValue(block, "title")),
      link: extractAtomLink(block),
      publishedAt:
        parseDate(extractTagValue(block, "published")) ||
        parseDate(extractTagValue(block, "updated")),
      summary: stripTags(
        extractTagValue(block, "summary") || extractTagValue(block, "content"),
      ),
    };
  });
}

export function parseFeed(xml, sourceLabel, categoryRules = CATEGORY_RULES) {
  const items = xml.includes("<entry") ? parseAtomEntries(xml, sourceLabel) : parseRssItems(xml, sourceLabel);

  return items
    .filter((item) => item.title && item.link && item.publishedAt)
    .map((item) => ({
      ...item,
      category: categorizeItem(item, categoryRules),
    }));
}

export function categorizeItem(item, categoryRules = CATEGORY_RULES) {
  const haystack = `${item.title} ${item.summary}`.toLowerCase();
  const bestRule = categoryRules
    .map((rule) => ({
      name: rule.name,
      score: rule.keywords.reduce(
        (count, keyword) => count + (haystack.includes(keyword) ? 1 : 0),
        0,
      ),
    }))
    .sort((a, b) => b.score - a.score)[0];

  return bestRule && bestRule.score > 0 ? bestRule.name : DEFAULT_CATEGORY_NAME;
}

function isWithinDays(date, days) {
  const threshold = new Date();
  threshold.setDate(threshold.getDate() - days);
  return date >= threshold;
}

async function fetchFeed(feed, categoryRules = CATEGORY_RULES) {
  const controller = new AbortController();
  const timeout = setTimeout(() => controller.abort(), REQUEST_TIMEOUT_MS);

  try {
    const response = await fetch(feed.url, {
      headers: {
        "user-agent": "saaf-rss-weekly-briefing/1.0",
        accept: "application/rss+xml, application/xml, text/xml, application/atom+xml, text/plain;q=0.5",
      },
      signal: controller.signal,
    });

    if (!response.ok) {
      throw new Error(`HTTP ${response.status}`);
    }

    const xml = await response.text();
    return {
      feed,
      items: parseFeed(xml, feed.label, categoryRules),
      error: null,
    };
  } catch (error) {
    return {
      feed,
      items: [],
      error: error instanceof Error ? error.message : String(error),
    };
  } finally {
    clearTimeout(timeout);
  }
}

export function buildReport(feedResults, options = {}) {
  const days = Number(options.days || REPORT_WINDOW_DAYS);
  const selectedCategories = uniqueByName(options.selectedCategories || []);
  const selectedFeeds = uniqueByName(options.selectedFeeds || []);

  const recentItems = feedResults
    .flatMap((result) => result.items)
    .filter((item) => isWithinDays(item.publishedAt, days))
    .filter((item) => selectedFeeds.length === 0 || selectedFeeds.includes(item.source))
    .filter((item) => selectedCategories.length === 0 || selectedCategories.includes(item.category))
    .sort((a, b) => b.publishedAt.getTime() - a.publishedAt.getTime());

  const categoryMap = new Map();
  for (const item of recentItems) {
    const bucket = categoryMap.get(item.category) || [];
    bucket.push(item);
    categoryMap.set(item.category, bucket);
  }

  const categoryEntries = [...categoryMap.entries()].sort((a, b) => b[1].length - a[1].length);
  const sourceCounts = recentItems.reduce((accumulator, item) => {
    accumulator[item.source] = (accumulator[item.source] || 0) + 1;
    return accumulator;
  }, {});

  const failedSources = feedResults.filter(
    (result) => result.error && (selectedFeeds.length === 0 || selectedFeeds.includes(result.feed.label)),
  );
  const intro = recentItems.length
    ? `In de afgelopen ${days} dagen zijn ${recentItems.length} berichten gevonden. De meeste aandacht ging naar ${categoryEntries
        .slice(0, 3)
        .map(([name, items]) => `${name} (${items.length})`)
        .join(", ")}.`
    : `Er zijn geen berichten gevonden in de afgelopen ${days} dagen.`;

  return {
    generatedAt: new Date(),
    days,
    intro,
    totalItems: recentItems.length,
    sourceCounts,
    categories: categoryEntries,
    failedSources,
    selectedFeeds,
    selectedCategories,
  };
}

export function renderHtml(report) {
  const sourceSummary = FEEDS.filter(
    (feed) => report.selectedFeeds.length === 0 || report.selectedFeeds.includes(feed.label),
  ).map((feed) => {
    const count = report.sourceCounts[feed.label] || 0;
    const note = feed.note ? `<div class="feed-note">${escapeHtml(feed.note)}</div>` : "";
    return `<li><strong>${escapeHtml(feed.label)}</strong>: ${count} artikelen${note}</li>`;
  }).join("");

  const activeFilters = [
    report.selectedFeeds.length ? `Feeds: ${report.selectedFeeds.join(", ")}` : "Feeds: alle",
    report.selectedCategories.length ? `Categorieen: ${report.selectedCategories.join(", ")}` : "Categorieen: alle",
  ].join(" | ");

  const failureHtml = report.failedSources.length
    ? `<section class="warnings"><h2>Bronnen met fouten</h2><ul>${report.failedSources
        .map(
          (result) =>
            `<li><strong>${escapeHtml(result.feed.label)}</strong>: ${escapeHtml(result.error || "Onbekende fout")}</li>`,
        )
        .join("")}</ul></section>`
    : "";

  const categoryHtml = report.categories.length
    ? report.categories
        .map(([category, items]) => {
          const headline = items[0];
          return `<section class="category">
            <h2>${escapeHtml(category)} <span>${items.length}</span></h2>
            <p class="category-summary">Belangrijkste recente item: <a href="${escapeHtml(headline.link)}">${escapeHtml(
              headline.title,
            )}</a> (${escapeHtml(headline.source)}).</p>
            <ul class="items">
              ${items
                .map(
                  (item) => `<li>
                    <a href="${escapeHtml(item.link)}">${escapeHtml(item.title)}</a>
                    <div class="meta">${escapeHtml(item.source)} | ${item.publishedAt.toLocaleString("nl-NL")}</div>
                    <p>${escapeHtml(item.summary || "Geen samenvatting beschikbaar.")}</p>
                  </li>`,
                )
                .join("")}
            </ul>
          </section>`;
        })
        .join("")
    : `<section class="category"><h2>Geen resultaten</h2><p>Er zijn geen publicaties binnen het ingestelde tijdvenster gevonden.</p></section>`;

  return `<!DOCTYPE html>
<html lang="nl">
  <head>
    <meta charset="utf-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1" />
    <title>Weekoverzicht DNB, AFM en FD</title>
    <style>
      :root {
        color-scheme: light;
        --bg: #f4efe7;
        --panel: rgba(255, 252, 247, 0.88);
        --panel-strong: #fffaf2;
        --ink: #1d2a33;
        --muted: #566773;
        --accent: #0d6b5d;
        --accent-soft: #d9efe9;
        --border: rgba(29, 42, 51, 0.12);
        --shadow: 0 18px 50px rgba(18, 35, 43, 0.12);
      }

      * {
        box-sizing: border-box;
      }

      body {
        margin: 0;
        font-family: Georgia, "Times New Roman", serif;
        color: var(--ink);
        background:
          radial-gradient(circle at top left, rgba(13, 107, 93, 0.18), transparent 30%),
          linear-gradient(180deg, #fbf8f2 0%, var(--bg) 100%);
      }

      main {
        max-width: 1100px;
        margin: 0 auto;
        padding: 40px 20px 72px;
      }

      .hero,
      .warnings,
      .category {
        background: var(--panel);
        backdrop-filter: blur(10px);
        border: 1px solid var(--border);
        border-radius: 24px;
        box-shadow: var(--shadow);
      }

      .hero {
        padding: 32px;
      }

      h1,
      h2 {
        margin: 0 0 16px;
        line-height: 1.1;
      }

      h1 {
        font-size: clamp(2.2rem, 5vw, 4.4rem);
      }

      h2 {
        font-size: clamp(1.4rem, 2vw, 2rem);
        display: flex;
        justify-content: space-between;
        align-items: baseline;
      }

      h2 span,
      .meta,
      .feed-note {
        color: var(--muted);
        font-size: 0.95rem;
      }

      .lede {
        max-width: 70ch;
        font-size: 1.1rem;
      }

      .grid {
        display: grid;
        gap: 20px;
        grid-template-columns: repeat(auto-fit, minmax(240px, 1fr));
        margin-top: 28px;
      }

      .stat {
        background: var(--panel-strong);
        border-radius: 18px;
        padding: 18px;
        border: 1px solid var(--border);
      }

      .stat strong {
        display: block;
        font-size: 2rem;
      }

      .warnings {
        margin-top: 20px;
        padding: 24px;
      }

      .category {
        margin-top: 20px;
        padding: 24px;
      }

      .items {
        list-style: none;
        padding: 0;
        margin: 18px 0 0;
        display: grid;
        gap: 16px;
      }

      .items li {
        padding-top: 16px;
        border-top: 1px solid var(--border);
      }

      .items li:first-child {
        padding-top: 0;
        border-top: 0;
      }

      a {
        color: var(--accent);
      }

      p {
        margin: 10px 0 0;
      }

      ul {
        padding-left: 20px;
      }

      @media (max-width: 640px) {
        main {
          padding: 20px 14px 48px;
        }

        .hero,
        .warnings,
        .category {
          border-radius: 18px;
          padding: 18px;
        }
      }
    </style>
  </head>
  <body>
    <main>
      <section class="hero">
        <h1>Weekoverzicht financieel nieuws</h1>
        <p class="lede">${escapeHtml(report.intro)}</p>
        <div class="grid">
          <div class="stat">
            <div>Gegenereerd op</div>
            <strong>${escapeHtml(report.generatedAt.toLocaleString("nl-NL"))}</strong>
          </div>
          <div class="stat">
            <div>Tijdsvenster</div>
            <strong>${report.days} dagen</strong>
          </div>
          <div class="stat">
            <div>Totaal berichten</div>
            <strong>${report.totalItems}</strong>
          </div>
        </div>
        <p class="meta" style="margin-top: 18px;">${escapeHtml(activeFilters)}</p>
        <h2 style="margin-top: 28px;">Bronverdeling <span>DNB, AFM, FD</span></h2>
        <ul>${sourceSummary}</ul>
        <p><a href="/">Nieuwe selectie maken</a></p>
      </section>
      ${failureHtml}
      ${categoryHtml}
    </main>
  </body>
</html>`;
}

function renderFeedOptions(selectedFeedKeys = FEEDS.map((feed) => feed.key)) {
  return FEEDS.map((feed) => {
    const checked = selectedFeedKeys.includes(feed.key) ? "checked" : "";
    return `<label class="feed-option">
      <input type="checkbox" name="feeds" value="${escapeHtml(feed.key)}" ${checked} />
      <span>
        <strong>${escapeHtml(feed.label)}</strong>
        <small>${escapeHtml(feed.url)}</small>
      </span>
    </label>`;
  }).join("");
}

function renderCategorySuggestions() {
  return getCategorySuggestions()
    .map((category) => `<option value="${escapeHtml(category)}"></option>`)
    .join("");
}

function renderHomePage(options = {}) {
  const selectedFeedKeys = options.selectedFeedKeys || FEEDS.map((feed) => feed.key);
  const selectedCategories = options.selectedCategories || [];
  return `<!DOCTYPE html>
<html lang="nl">
  <head>
    <meta charset="utf-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1" />
    <title>SAAF RSS Nieuwsapp</title>
    <style>
      :root {
        --bg: #f4efe7;
        --panel: rgba(255, 252, 247, 0.94);
        --ink: #1d2a33;
        --muted: #566773;
        --accent: #0d6b5d;
        --border: rgba(29, 42, 51, 0.12);
      }

      body {
        margin: 0;
        min-height: 100vh;
        background: linear-gradient(135deg, #f4efe7, #e0efe7);
        font-family: Georgia, "Times New Roman", serif;
        color: var(--ink);
      }

      main {
        max-width: 960px;
        margin: 0 auto;
        padding: 28px 16px 48px;
      }

      article {
        width: 100%;
        background: var(--panel);
        border: 1px solid var(--border);
        border-radius: 24px;
        padding: 32px;
        box-shadow: 0 18px 50px rgba(18, 35, 43, 0.12);
      }

      form {
        display: grid;
        gap: 28px;
        margin-top: 28px;
      }

      .section {
        display: grid;
        gap: 14px;
      }

      .feeds {
        display: grid;
        gap: 12px;
      }

      .feed-option {
        display: flex;
        gap: 12px;
        align-items: flex-start;
        padding: 14px 16px;
        border-radius: 16px;
        border: 1px solid var(--border);
        background: rgba(255, 255, 255, 0.6);
      }

      .feed-option small,
      .hint {
        display: block;
        color: var(--muted);
      }

      input[type="text"] {
        width: 100%;
        padding: 14px 16px;
        border-radius: 14px;
        border: 1px solid var(--border);
        font: inherit;
        background: white;
      }

      button {
        border: 0;
        border-radius: 999px;
        padding: 14px 20px;
        font: inherit;
        background: var(--accent);
        color: white;
        cursor: pointer;
        width: fit-content;
      }

      a {
        color: var(--accent);
      }

      @media (max-width: 640px) {
        article {
          padding: 20px;
          border-radius: 18px;
        }
      }
    </style>
  </head>
  <body>
    <main>
      <article>
        <h1>SAAF RSS Nieuwsapp</h1>
        <p>Maak hier je selectie en genereer daarna een HTML-weekoverzicht voor de afgelopen ${REPORT_WINDOW_DAYS} dagen.</p>
        <form action="/report" method="get">
          <section class="section">
            <h2>RSS feeds</h2>
            <div class="feeds">${renderFeedOptions(selectedFeedKeys)}</div>
          </section>
          <section class="section">
            <h2>Categorieen</h2>
            <label for="categories">Vul een of meer categorieen in, gescheiden door komma's.</label>
            <input
              id="categories"
              name="categories"
              type="text"
              list="category-suggestions"
              placeholder="Bijvoorbeeld: Toezicht en regelgeving, Klimaat, Overig"
              value="${escapeHtml(selectedCategories.join(", "))}"
            />
            <datalist id="category-suggestions">
              ${renderCategorySuggestions()}
            </datalist>
            <p class="hint">Je kunt bestaande suggesties kiezen of eigen categorieen invoeren. Eigen categorieen worden als extra trefwoorden gebruikt bij het indelen van artikelen.</p>
          </section>
          <button type="submit">Genereer HTML-overzicht</button>
        </form>
        <p class="hint">Optioneel kun je <code>DNB_FEED_URL</code>, <code>AFM_FEED_URL</code>, <code>FD_FEED_URL</code>, <code>REPORT_WINDOW_DAYS</code> en <code>PORT</code> via environment variables overschrijven.</p>
      </article>
    </main>
  </body>
</html>`;
}

const server = http.createServer(async (request, response) => {
  const url = new URL(request.url || "/", `http://${request.headers.host}`);

  if (request.method !== "GET") {
    response.writeHead(405, { "content-type": "text/plain; charset=utf-8" });
    response.end("Method not allowed");
    return;
  }

  if (url.pathname === "/") {
    response.writeHead(200, { "content-type": "text/html; charset=utf-8" });
    response.end(renderHomePage());
    return;
  }

  if (url.pathname === "/report") {
    const selectedFeedKeys = uniqueByName(url.searchParams.getAll("feeds"));
    const selectedFeeds = FEEDS.filter(
      (feed) => selectedFeedKeys.length === 0 || selectedFeedKeys.includes(feed.key),
    );
    const selectedCategories = uniqueByName(splitCategoryInput(url.searchParams.get("categories") || ""));
    const categoryRules = buildCategoryRules(selectedCategories);
    const feedResults = await Promise.all(selectedFeeds.map((feed) => fetchFeed(feed, categoryRules)));
    const report = buildReport(feedResults, {
      days: REPORT_WINDOW_DAYS,
      selectedFeeds: selectedFeeds.map((feed) => feed.label),
      selectedCategories,
    });
    response.writeHead(200, { "content-type": "text/html; charset=utf-8" });
    response.end(renderHtml(report));
    return;
  }

  response.writeHead(404, { "content-type": "text/plain; charset=utf-8" });
  response.end("Not found");
});

const entryFile = process.argv[1] ? path.resolve(process.argv[1]) : "";
const currentFile = fileURLToPath(import.meta.url);

if (entryFile === currentFile) {
  server.on("error", (error) => {
    console.error(error instanceof Error ? error.message : String(error));
    process.exitCode = 1;
  });

  server.listen(PORT, HOST, () => {
    console.log(`Server listening on http://${HOST}:${PORT}`);
  });
}

export {
  buildCategoryRules,
  FEEDS,
  getCategorySuggestions,
  server,
  splitCategoryInput,
};
