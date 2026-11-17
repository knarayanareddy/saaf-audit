import test from "node:test";
import assert from "node:assert/strict";

import {
  buildCategoryRules,
  buildReport,
  categorizeItem,
  FEEDS,
  parseFeed,
  splitCategoryInput,
} from "./server.js";

test("parseFeed parses RSS items and applies categories", () => {
  const xml = `<?xml version="1.0"?>
  <rss version="2.0">
    <channel>
      <item>
        <title>AFM scherpt toezicht op crypto aan</title>
        <link>https://example.com/crypto</link>
        <pubDate>${new Date().toUTCString()}</pubDate>
        <description><![CDATA[Meer toezicht en compliance voor aanbieders.]]></description>
      </item>
    </channel>
  </rss>`;

  const items = parseFeed(xml, "AFM");
  assert.equal(items.length, 1);
  assert.equal(items[0].source, "AFM");
  assert.equal(items[0].category, "Toezicht en regelgeving");
});

test("categorizeItem falls back to Overig when no rule matches", () => {
  const category = categorizeItem({
    title: "Algemeen nieuwsbericht",
    summary: "Zonder specifieke trefwoorden",
  });

  assert.equal(category, "Overig");
});

test("buildReport groups recent items per category", () => {
  const now = new Date();
  const feedResults = [
    {
      feed: { label: "DNB" },
      error: null,
      items: [
        {
          source: "DNB",
          title: "Nieuwe inflatieverwachting",
          link: "https://example.com/dnb",
          publishedAt: now,
          summary: "Economische groei en inflatie staan centraal.",
          category: "Monetair en economie",
        },
      ],
    },
    {
      feed: { label: "AFM" },
      error: "timeout",
      items: [],
    },
  ];

  const report = buildReport(feedResults, {
    days: 7,
    selectedFeeds: ["DNB", "AFM"],
  });
  assert.equal(report.totalItems, 1);
  assert.equal(report.categories.length, 1);
  assert.equal(report.categories[0][0], "Monetair en economie");
  assert.equal(report.failedSources.length, 1);
});

test("DNB default feed uses the current RSS endpoint", () => {
  const dnbFeed = FEEDS.find((feed) => feed.key === "dnb");
  assert.ok(dnbFeed);
  assert.equal(dnbFeed.url, "https://www.dnb.nl/nl/rss/16451/6882");
});

test("splitCategoryInput normalizes comma separated categories", () => {
  const categories = splitCategoryInput(" Toezicht en regelgeving, Klimaat , Klimaat ");
  assert.deepEqual(categories, ["Toezicht en regelgeving", "Klimaat", "Klimaat"]);
});

test("custom categories are appended to rule matching", () => {
  const rules = buildCategoryRules(["Crypto toezicht"]);
  const category = categorizeItem(
    {
      title: "AFM intensiveert crypto toezicht",
      summary: "Nieuwe eisen voor crypto aanbieders",
    },
    rules,
  );

  assert.equal(category, "Crypto toezicht");
});

test("buildReport filters on selected categories", () => {
  const now = new Date();
  const feedResults = [
    {
      feed: { label: "DNB" },
      error: null,
      items: [
        {
          source: "DNB",
          title: "Nieuwe inflatieverwachting",
          link: "https://example.com/dnb",
          publishedAt: now,
          summary: "Economische groei en inflatie staan centraal.",
          category: "Monetair en economie",
        },
        {
          source: "DNB",
          title: "Cyber weerbaarheid omhoog",
          link: "https://example.com/dnb-cyber",
          publishedAt: now,
          summary: "Security en data governance",
          category: "Digitalisering en cyber",
        },
      ],
    },
  ];

  const report = buildReport(feedResults, {
    days: 7,
    selectedFeeds: ["DNB"],
    selectedCategories: ["Digitalisering en cyber"],
  });

  assert.equal(report.totalItems, 1);
  assert.equal(report.categories[0][0], "Digitalisering en cyber");
});
