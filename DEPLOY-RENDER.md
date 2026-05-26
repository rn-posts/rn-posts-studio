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

### Firebase (obrigatório para o app React)

O Vite **embute** as variáveis no JavaScript no momento do **build**.  
Sem elas no Render, o navegador mostra `auth/invalid-api-key`.

Em **Environment**, adicione (copie do seu `.env` local):

| Variável | Exemplo de origem |
|----------|-------------------|
| `VITE_FIREBASE_API_KEY` | Firebase Console → Config do app Web |
| `VITE_FIREBASE_AUTH_DOMAIN` | `*.firebaseapp.com` |
| `VITE_FIREBASE_PROJECT_ID` | ID do projeto |
| `VITE_FIREBASE_STORAGE_BUCKET` | `*.firebasestorage.app` |
| `VITE_FIREBASE_MESSAGING_SENDER_ID` | número do projeto |
| `VITE_FIREBASE_APP_ID` | `1:...:web:...` |

Opcional: `VITE_MAKE_WEBHOOK_URL` (publicação via Make).

Depois de salvar → **Manual Deploy** (precisa rebuildar o frontend).

### API Python (runtime)

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
