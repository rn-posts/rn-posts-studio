"""
python-api/estilos_acabamento_v88.py  —  v88  —  bloco de ACABAMENTO FOTOGRÁFICO detalhado para os 20 estilos

Por quê: Cinematic e Showcase têm um prompt mais detalhado (lente, profundidade de campo, textura, tons elegantes,
sombras suaves, contraste equilibrado, acabamento premium, realismo, "sem aparência artificial"), e por isso saem
mais sofisticados. Os outros 20 estilos só descreviam a metáfora. Aqui cada um ganha o MESMO tipo de bloco, adaptado
à sua natureza (macro, atmosfera, still life, arquitetura, tecido, papel, pigmento...).

Como entra: texto de prompt apenas (zero chamadas extras, zero memória). É ACRESCENTADO ao conceito/cena do estilo,
nunca substitui nada:
  • estilos_prompts_v71.montar()  -> conceito + acabamento (caminho normal dos 20 estilos)
  • estilos_card (fim do catálogo) -> ESTILOS[k]["cena"] + acabamento (caminho do Com Ronilson e do fallback)
Cinematic e Showcase não estão aqui: já têm o seu. Para desligar um estilo, apague a chave dele. ACABAMENTO_V88 = {} desliga tudo.

Estilos: gold (Kintsugi), smoke (Fumaça), portal (Portal), ice (Gelo), floating (Flutuante), macro (Macro), museum (Museu),
sprout (Broto), roots (Raízes), stone (Pedra), bluehour (Hora azul), shadow (Sombra e luz), lamp (Abrigo de luz),
thread (Fio e tecido), mirror (Espelho), paper (Papel), mosaic (Mosaico), shelter (Refúgio), path (Caminho),
watercolor (Aquarela).
"""

ACABAMENTO_V88 = {
    # ── Kintsugi: fine art, ouro de verdade, cerâmica de verdade
    "gold": (
        "sophisticated fine-art still life photography, 100mm macro-capable lens, razor-thin depth of field with the gold "
        "seams tack-sharp, realistic metallic lacquer sheen with tiny natural irregularities, authentic matte ceramic glaze "
        "texture, elegant muted tones, soft shadows, balanced contrast, premium museum-catalogue finish, high definition, "
        "authentic photographic realism, without artificial appearance"
    ),
    # ── Fumaça: fluido convincente, borda translúcida
    "smoke": (
        "sophisticated atmospheric photography, 85mm lens with soft depth of field, convincing fluid dynamics with delicate "
        "translucent edges frozen by a fast exposure, realistic soft light scattering through the vapor, elegant tones, soft "
        "shadows, balanced contrast, premium photographic appearance, high definition, authentic photographic realism, "
        "never CGI-looking, without artificial appearance"
    ),
    # ── Portal: arquitetura em luz natural
    "portal": (
        "sophisticated architectural photography with a cinematic feel, 35mm lens, soft depth of field that keeps the "
        "threshold crisp, believable soft light entering through the opening, realistic wood, stone and plaster texture, "
        "elegant warm-to-cool tonal contrast, soft shadows, balanced exposure with detail kept in the highlights, premium "
        "photographic appearance, high definition, authentic photographic realism, without artificial appearance"
    ),
    # ── Gelo: transparência e refração críveis
    "ice": (
        "sophisticated macro still life photography, 100mm macro lens, shallow depth of field, crisp realistic ice, frost "
        "and condensation detail with believable refraction and transparency, elegant cool tones with one warm point of "
        "light, soft shadows, balanced contrast, premium photographic appearance, high definition, authentic photographic "
        "realism, without artificial appearance"
    ),
    # ── Flutuante: estética de campanha, sem fios visíveis
    "floating": (
        "sophisticated minimalist campaign-style photography, 70mm lens, clean composition with every object tack-sharp, "
        "believable soft shadows and a subtle tonal falloff in the backdrop, authentic materials and micro-texture, elegant "
        "tones, balanced contrast, premium finish, high definition, authentic photographic realism, no visible wires or "
        "supports, without artificial appearance"
    ),
    # ── Macro: joia, foco na textura
    "macro": (
        "sophisticated extreme macro photography, 100mm macro lens, razor-thin depth of field, tack-sharp micro-texture on "
        "the focal plane, creamy bokeh, jewel-like highlights, elegant tones, soft shadows, balanced contrast, premium "
        "photographic appearance, high definition, authentic photographic realism, without artificial appearance"
    ),
    # ── Museu: luz controlada de galeria
    "museum": (
        "sophisticated gallery photography, 50mm lens at eye level, controlled museum lighting with a precise soft pool of "
        "light and gentle falloff, refined plaster and stone texture, restrained elegant tones, soft shadows, balanced "
        "contrast, premium fine-art finish, high definition, authentic photographic realism, without artificial appearance"
    ),
    # ── Broto: botânico, translucidez, orvalho
    "sprout": (
        "sophisticated botanical close-up photography, 90mm macro lens, shallow depth of field with the new growth "
        "tack-sharp, translucent leaf detail under soft backlight with natural dew, authentic soil and stone texture, fresh "
        "elegant greens against calm deep tones, soft shadows, balanced contrast, premium photographic appearance, high "
        "definition, authentic photographic realism, without artificial appearance"
    ),
    # ── Raízes: natureza de arte, textura rica
    "roots": (
        "sophisticated fine-art nature photography, 50mm lens, moderate depth of field, rich authentic bark, moss and soil "
        "texture, soft diffused light revealing every ridge, elegant earthy tones, soft shadows, balanced contrast without "
        "crushed blacks, premium photographic appearance, high definition, authentic photographic realism, without "
        "artificial appearance"
    ),
    # ── Pedra: mineral fosco, grão real
    "stone": (
        "sophisticated minimalist still life photography, 85mm lens, shallow-to-moderate depth of field, matte mineral "
        "texture with realistic grain and tiny imperfections, soft side light, elegant muted tones, soft shadows, balanced "
        "contrast, premium photographic appearance, high definition, authentic photographic realism, without artificial "
        "appearance"
    ),
    # ── Hora azul: gradiente suave, sem banding
    "bluehour": (
        "sophisticated blue hour photography with a cinematic feel, 35mm lens, soft depth of field, smooth natural gradient "
        "from deep navy to warm orange without banding, realistic soft atmospheric glow, elegant cool-to-warm tonal "
        "contrast, soft shadows, balanced exposure, fine film-like grain, premium photographic appearance, high definition, "
        "authentic photographic realism, without artificial appearance"
    ),
    # ── Sombra e luz: sombra de borda suave, detalhe nas duas áreas
    "shadow": (
        "sophisticated fine-art light and shadow photography, 50mm lens, clean minimalist composition, crisp yet soft-edged "
        "shadow shapes with natural falloff, authentic plaster, wood and fabric texture, elegant tones, balanced contrast "
        "with detail kept in both light and shade, premium gallery finish, high definition, authentic photographic realism, "
        "without artificial appearance"
    ),
    # ── Abrigo de luz: pouca luz, sem estourar
    "lamp": (
        "sophisticated low-light photography, 50mm lens at a wide aperture, subtle bokeh around the warm glow, realistic "
        "flame or lamp light with natural falloff and no blown-out highlights, authentic wood, linen and ceramic texture, "
        "elegant warm-and-cool tones, soft shadows, balanced contrast, premium cinematic appearance, high definition, "
        "authentic photographic realism, without artificial appearance"
    ),
    # ── Fio e tecido: macro têxtil, fibra por fibra
    "thread": (
        "sophisticated textile macro photography, 90mm macro lens, shallow depth of field with every fibre and weave "
        "tack-sharp, soft grazing light that reveals texture, a subtle realistic sheen on the gold thread, elegant tones, "
        "soft shadows, balanced contrast, premium editorial appearance, high definition, authentic photographic realism, "
        "without artificial appearance"
    ),
    # ── Espelho: reflexo controlado, sem brilho estourado
    "mirror": (
        "sophisticated fine-art still life photography, 70mm lens, controlled reflections that show only light, sky and "
        "plants, clean specular highlights without glare, authentic polished-surface and glass detail, elegant restrained "
        "tones, soft shadows, balanced contrast, premium photographic appearance, high definition, authentic photographic "
        "realism, without artificial appearance"
    ),
    # ── Papel: fibra do papel, sem texto legível
    "paper": (
        "sophisticated tactile still life photography, 85mm lens, shallow depth of field, visible paper fibre, grain and "
        "fold detail under soft window light, no legible text, elegant warm-neutral tones, soft shadows, balanced contrast, "
        "premium editorial appearance, high definition, authentic photographic realism, without artificial appearance"
    ),
    # ── Mosaico: vidro, esmalte e cerâmica de verdade
    "mosaic": (
        "sophisticated fine-art still life photography, 85mm lens, crisp focus across the arrangement with a gentle falloff "
        "at the edges, authentic glaze, glass and ceramic texture with tiny natural irregularities, harmonious elegant "
        "tones, soft shadows, balanced contrast, premium photographic appearance, high definition, authentic photographic "
        "realism, without artificial appearance"
    ),
    # ── Refúgio: aconchego real, nada de catálogo
    "shelter": (
        "sophisticated lifestyle photography, 35mm lens, soft depth of field, authentic knitted, linen and wood texture, "
        "warm gentle light with natural falloff, elegant cozy tones, soft shadows, balanced contrast, premium photographic "
        "appearance, high definition, authentic photographic realism, never staged or catalogue-like, without artificial "
        "appearance"
    ),
    # ── Caminho: profundidade em camadas, névoa leve
    "path": (
        "sophisticated cinematic photography, 35mm lens, layered depth with a softly misted background, authentic stone, "
        "earth and leaf texture, soft natural light, elegant tones, soft shadows, balanced contrast, premium photographic "
        "appearance, high definition, authentic photographic realism, without artificial appearance"
    ),
    # ── Aquarela: pigmento molhado de verdade, não gradiente digital
    "watercolor": (
        "sophisticated fine-art abstract photograph of real wet pigment on paper, 100mm macro lens, authentic cotton-paper "
        "grain, natural pigment pooling, soft feathered edges and layered translucency, elegant tones, soft shadows, "
        "balanced contrast, premium gallery finish, high definition, authentic photographic realism, not a flat digital "
        "gradient, without artificial appearance"
    ),
}


def acabamento(estilo):
    """Texto de acabamento do estilo (ou None se o estilo não tem / já tem o seu, como Cinematic e Showcase)."""
    return ACABAMENTO_V88.get(estilo)
