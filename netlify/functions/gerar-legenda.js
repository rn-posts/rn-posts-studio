// netlify/functions/gerar-legenda.js
// Gera legenda via Gemini, OpenAI ou Claude — troca pelo env AI_PROVIDER

const fetch = (...args) => import("node-fetch").then(({ default: f }) => f(...args));

const PROMPT = (tema) =>
  `Crie uma legenda para um post do Instagram da AlvoreSer, clínica de psicologia, ` +
  `sobre o tema: "${tema}". ` +
  `Tom: acolhedor, humano, não-clínico, para o público geral. ` +
  `Máximo 150 palavras. Inclua 5 hashtags relevantes no final. ` +
  `Retorne apenas o texto da legenda, sem explicações adicionais.`;

async function gerarGemini(tema) {
  const url = `https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent?key=${process.env.GEMINI_API_KEY}`;
  const res = await fetch(url, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ contents: [{ parts: [{ text: PROMPT(tema) }] }] }),
  });
  const data = await res.json();
  return data.candidates?.[0]?.content?.parts?.[0]?.text || "";
}

async function gerarOpenAI(tema) {
  const res = await fetch("https://api.openai.com/v1/chat/completions", {
    method: "POST",
    headers: {
      "Authorization": `Bearer ${process.env.OPENAI_API_KEY}`,
      "Content-Type": "application/json",
    },
    body: JSON.stringify({
      model: "gpt-4o-mini",
      messages: [{ role: "user", content: PROMPT(tema) }],
      max_tokens: 400,
    }),
  });
  const data = await res.json();
  return data.choices?.[0]?.message?.content || "";
}

async function gerarClaude(tema) {
  const res = await fetch("https://api.anthropic.com/v1/messages", {
    method: "POST",
    headers: {
      "x-api-key": process.env.CLAUDE_API_KEY,
      "anthropic-version": "2023-06-01",
      "Content-Type": "application/json",
    },
    body: JSON.stringify({
      model: "claude-haiku-4-5-20251001",
      max_tokens: 400,
      messages: [{ role: "user", content: PROMPT(tema) }],
    }),
  });
  const data = await res.json();
  return data.content?.[0]?.text || "";
}

exports.handler = async (event) => {
  if (event.httpMethod !== "POST") {
    return { statusCode: 405, body: JSON.stringify({ erro: "Método não permitido" }) };
  }

  let body;
  try { body = JSON.parse(event.body); }
  catch { return { statusCode: 400, body: JSON.stringify({ erro: "JSON inválido" }) }; }

  const { tema = "", provider = process.env.AI_PROVIDER || "gemini" } = body;

  if (!tema.trim()) {
    return { statusCode: 400, body: JSON.stringify({ erro: "Tema obrigatório" }) };
  }

  try {
    let legenda = "";
    if (provider === "openai")  legenda = await gerarOpenAI(tema);
    else if (provider === "claude") legenda = await gerarClaude(tema);
    else legenda = await gerarGemini(tema);

    return { statusCode: 200, body: JSON.stringify({ legenda, provider }) };
  } catch (e) {
    console.error("Erro IA:", e.message);
    return { statusCode: 500, body: JSON.stringify({ erro: e.message }) };
  }
};
