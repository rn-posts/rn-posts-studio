import os
import cloudinary, cloudinary.api

cloudinary.config(
    cloud_name="dxfxlwfjq",
    api_key="341158176522493",
    api_secret="uANWmV05UShwpSNlTEHX-nYz5l0",
)

pastas = [
    "Banco de Imagens/Acolhimento",
    "Banco de Imagens/Ansiedade e Estresse",
    "Banco de Imagens/Autismo",
    "Banco de Imagens/Borderline",
    "Banco de Imagens/Convite e Terapia",
    "Banco de Imagens/Depressão",
    "Banco de Imagens/Recomeço e Transformação",
    "Banco de Imagens/Ronilson",
    "Banco de Imagens/TDAH",
]

for p in pastas:
    try:
        # Tenta sem barra no final e com barra no final
        res = cloudinary.api.resources(type="upload", prefix=p, max_results=10)
        recursos = res.get("resources", [])
        print(f"Pasta '{p}' (prefix={p}) -> Encontrados {len(recursos)} recursos")
        for r in recursos:
            print(f"   - PID: {r['public_id']} | URL: {r['secure_url']}")
    except Exception as e:
        print(f"Erro ao listar '{p}': {e}")
