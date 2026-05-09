// netlify/functions/gerar-legenda.js
// Redireciona para a API Python no Render
// O Render é quem gera a legenda com Gemini + assinatura fixa

exports.handler = async (event) => {
  if (event.httpMethod !== "POST") {
    return { statusCode: 405, body: JSON.stringify({ erro: "Método não permitido" }) };
  }

  const RENDER_URL = process.env.RENDER_URL;
  if (!RENDER_URL) {
    return { statusCode: 500, body: JSON.stringify({ erro: "RENDER_URL não configurada" }) };
  }

  try {
    const body = JSON.parse(event.body);
    const res  = await fetch(`${RENDER_URL}/gerar-legenda`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ tema: body.tema }),
    });
    const data = await res.json();
    return {
      statusCode: res.status,
      body: JSON.stringify(data),
    };
  } catch (e) {
    return { statusCode: 500, body: JSON.stringify({ erro: e.message }) };
  }
};
