# Deploy no Render — rn-posts.onrender.com

## Problema (404 na raiz)

O Flask serve o React em `dist/index.html`. Se o **build do frontend** não roda no deploy, a pasta `dist` não existe e `https://rn-posts.onrender.com/` retorna **404**.

A API continua funcionando: `https://rn-posts.onrender.com/health`

## Configuração no painel Render

Em **Settings** do serviço `rn-posts`:

| Campo | Valor |
|--------|--------|
| **Root Directory** | *(vazio — raiz do repositório)* |
| **Build Command** | `npm ci && npm run build && pip install -r python-api/requirements.txt` |
| **Start Command** | `cd python-api && gunicorn main:app --bind 0.0.0.0:$PORT --workers 1 --timeout 120` |

Variáveis de ambiente obrigatórias (já devem estar no serviço):

- `CLOUDINARY_CLOUD_NAME`, `CLOUDINARY_API_KEY`, `CLOUDINARY_API_SECRET`
- `GROQ_API_KEY` e/ou `GEMINI_API_KEY`
- `GOOGLE_SERVICE_ACCOUNT_JSON`

## Depois de alterar

1. **Manual Deploy** → Deploy latest commit  
2. Aguarde o build terminar (log deve mostrar `vite build` e criar `dist/`)  
3. Abra `https://rn-posts.onrender.com/` — deve carregar o app  

## Fontes dos cards

As fontes devem existir em `src/Brand/fonts/` (ou `python-api/fonts/`) com estes nomes exatos (Linux é sensível a maiúsculas):

- `AGILERA.OTF`
- `MALGUN.TTF`, `MALGUNBD.TTF`, `MALGUNSL.TTF`

Confira em `/health` → `agilera_ok: true`.
