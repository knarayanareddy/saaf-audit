const OpenAI = require("openai");
const client = new OpenAI();

async function summarise(config) {
  // no untrusted text: only fixed config values reach the prompt
  const prompt = `Summarise the ${config.period} incident statistics for ${config.team}.`;
  return client.chat.completions.create({ model: "x", messages: [{ role: "user", content: prompt }] });
}
module.exports = { summarise };
