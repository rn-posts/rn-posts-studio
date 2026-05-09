// netlify/functions/gerar-card.js
exports.handler = async (event) => {
  if (event.httpMethod !== "POST") {
    return { statusCode: 405, body: JSON.stringify({ erro: "Método não permitido" }) };
  }

  let body;
  try {
    body = JSON.parse(event.body);
  } catch {
    return { statusCode: 400, body: JSON.stringify({ erro: "JSON inválido" }) };
  }

  const { tema = "", legenda = "" } = body;

  if (!tema.trim()) {
    return { statusCode: 400, body: JSON.stringify({ erro: "Tema obrigatório" }) };
  }

  try {
    const response = await fetch("https://alvoreser-python-api.onrender.com/gerar-card", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ tema, legenda }),
      signal: AbortSignal.timeout(25000),
    });

    if (!response.ok) {
      const erro = await response.text();
      throw new Error(`Render retornou ${response.status}: ${erro}`);
    }

    const data = await response.json();
    return { statusCode: 200, body: JSON.stringify(data) };

  } catch (e) {
    console.error("Erro ao chamar Render:", e.message);
    return { statusCode: 502, body: JSON.stringify({ erro: e.message }) };
  }
};