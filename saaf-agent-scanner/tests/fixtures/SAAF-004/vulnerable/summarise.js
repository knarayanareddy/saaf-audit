const OpenAI = require("openai");
const client = new OpenAI();

async function summarise(ticketText) {
  const prompt = `Summarise the following incident ticket and classify materiality:\n${ticketText}`;
  return client.chat.completions.create({ model: "x", messages: [{ role: "user", content: prompt }] });
}
module.exports = { summarise };
