// netlify/functions/gerar-card.js
// Chama um script Python local (via spawn) que gera o card e sobe no Cloudinary

const { execSync } = require("child_process");
const path = require("path");

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
    // Chama o script Python passando tema e legenda como argumentos
    // O script imprime a URL do Cloudinary no stdout
    const scriptPath = path.join(__dirname, "../../scripts/gerar_card.py");

    const stdout = execSync(
      `python3 "${scriptPath}" "${tema.replace(/"/g, '\\"')}" "${legenda.replace(/"/g, '\\"')}"`,
      {
        env: {
          ...process.env,
          CLOUDINARY_CLOUD_NAME: process.env.CLOUDINARY_CLOUD_NAME,
          CLOUDINARY_API_KEY:    process.env.CLOUDINARY_API_KEY,
          CLOUDINARY_API_SECRET: process.env.CLOUDINARY_API_SECRET,
        },
        timeout: 30000,
      }
    ).toString().trim();

    // Última linha do stdout é a URL
    const lines = stdout.split("\n");
    const cloudinary_url = lines[lines.length - 1];

    if (!cloudinary_url.startsWith("https://")) {
      throw new Error("Script não retornou URL válida: " + cloudinary_url);
    }

    return {
      statusCode: 200,
      body: JSON.stringify({ cloudinary_url }),
    };
  } catch (e) {
    console.error("Erro ao gerar card:", e.message);
    return {
      statusCode: 500,
      body: JSON.stringify({ erro: e.message }),
    };
  }
};
