"""
python-api/estilos_card.py  —  v54  —  Estilos visuais de alta qualidade (IA com a paleta da clínica)

Rota própria: POST /preview-card-estilo

ESTILOS VISUAIS:
  * Cinematic: visual cinematográfico sofisticado, iluminação dramática e natural, luz suave e volumétrica,
               profundidade de campo, contraste equilibrado, composição de filme, enquadramento profissional,
               atmosfera envolvente, textura realista, tons elegantes, sombras suaves, aparência fotográfica premium,
               lente cinematográfica, bokeh sutil, alta definição, sem aparência artificial.
  * Showcase: apresentação premium do elemento principal, composição limpa e sofisticada, foco absoluto no
              objeto ou personagem, iluminação de estúdio cuidadosamente posicionada, fundo elegante e discreto,
              profundidade visual, detalhes nítidos, aparência profissional, estética de campanha publicitária,
              realismo elevado, acabamento premium, composição visual equilibrada.
  * Kintsugi, Fumaça, Portal, Gelo, Flutuante, Macro, Museu: metáforas poéticas com a paleta da clínica.
"""
import base64
import io
import json
import os
import random
import sys
import time
import traceback
import uuid

import numpy as np
import requests
from flask import Blueprint, jsonify, request
from PIL import Image, ImageEnhance, ImageFilter

bp = Blueprint("estilos_card", __name__)


def _m():
    """Módulo principal (main.py) já carregado — usado somente para leitura."""
    return sys.modules.get("main") or sys.modules.get("__main__")


class ErroEstilo(Exception):
    """Falha esperada ao montar o card de um estilo (mensagem vai para a tela)."""


_ETAPA = {"v": "inicio"}


# ── Catálogo de estilos visuais ────────────────────────────────────────────────
ESTILOS = {
    "cinematic": {
        "tipo": "cena",
        "rotulo": "Cinematic",
        "luz": "dramatic and natural cinematic lighting, soft and volumetric light, 35mm lens, subtle bokeh",
        "cena": (
            "sophisticated cinematic film still visual, film composition, professional framing, "
            "immersive atmosphere, realistic texture, elegant tones, soft shadows, premium photographic appearance, "
            "cinematic lens, subtle bokeh, high definition, balanced contrast, authentic photographic realism, "
            "without artificial appearance"
        ),
    },
    "showcase": {
        "tipo": "cena",
        "rotulo": "Showcase",
        "luz": "carefully positioned studio lighting, soft key light and gentle fill, elegant refined rim highlights",
        "cena": (
            "premium showcase presentation of the main symbolic element or subject, clean and sophisticated composition, "
            "absolute focus on the central subject, carefully positioned studio lighting, elegant and discreet background, "
            "visual depth, sharp details, professional appearance, advertising campaign aesthetic, elevated realism, "
            "premium finish, balanced visual composition"
        ),
    },
    "gold": {
        "tipo": "cena",
        "rotulo": "Kintsugi",
        "luz": "soft dawn side-light with warm solar-orange glints on the gold",
        "cena": (
            "a single handmade ceramic bowl in matte deep navy and petroleum teal glaze, "
            "broken and beautifully mended with luminous gold seams (kintsugi), resting "
            "on dark stone, shallow depth of field, the gold veins catching light"
        ),
    },
    "smoke": {
        "tipo": "cena",
        "rotulo": "Fumaça",
        "luz": "low warm solar-orange dawn glow backlighting the mist",
        "cena": (
            "slow ribbons of soft mist and smoke dissolving upward into clear air, "
            "deep navy and petroleum teal atmosphere, weightless, calm, tension dissipating"
        ),
    },
    "portal": {
        "tipo": "cena",
        "rotulo": "Portal",
        "luz": "golden-orange sunrise light flooding in from outside the doorway",
        "cena": (
            "an open wooden doorway seen from a quiet dark interior, bright dawn light "
            "and soft sage plants at the threshold, an invitation to take the first step, "
            "no one in frame"
        ),
    },
    "ice": {
        "tipo": "cena",
        "rotulo": "Gelo",
        "luz": "first warm solar-orange light refracting through the ice",
        "cena": (
            "clear ice slowly melting into still transparent water, teal and petroleum "
            "reflections, fine droplets, the thaw of frozen feelings, hope"
        ),
    },
    "floating": {
        "tipo": "cena",
        "rotulo": "Flutuante",
        "luz": "soft diffused dawn light, gentle shadows",
        "cena": (
            "three or four simple symbolic objects gently suspended in mid-air with lots of "
            "empty space: a ceramic cup, a few leaves, a thin golden thread, on a smooth "
            "petroleum teal to navy gradient backdrop, minimal and airy"
        ),
    },
    "macro": {
        "tipo": "cena",
        "rotulo": "Macro",
        "luz": "a single point of solar-orange light in creamy bokeh",
        "cena": (
            "extreme macro close-up of a dewdrop resting on a sage-green leaf vein, razor-thin "
            "depth of field, creamy teal bokeh, jewel-like premium detail"
        ),
    },
    "museum": {
        "tipo": "cena",
        "rotulo": "Museu",
        "luz": "a single soft museum spotlight from above",
        "cena": (
            "one small symbolic object displayed like a work of art in a minimal elegant "
            "gallery: a mended ceramic piece on a low plinth, deep navy wall with a subtle "
            "petroleum gradient, silent, refined, premium"
        ),
    },
}


# v55b: ajustes pequenos e independentes para Cinematic/Showcase (False desliga)
_AJUSTE_POSICAO_TEXTO = False  # v55c: desligado (dependia do Haar frontal, que nao ve perfil); substituido por _TITULO_INTELIGENTE
_REALISMO_SUAVE = False        # v55c: desligado para o rosto de frente repetir o prompt original (v54)
_ESTILOS_COM_PESSOA = ("cinematic", "showcase")
_TOQUE_REALISMO = (
    "If a person appears: natural unretouched skin with gentle texture, relaxed natural eyes with a soft "
    "natural gaze and normal proportions, no airbrushing, no plastic or glossy look."
)


# v55c: variantes de cena para Cinematic/Showcase (alternam a cada geracao)
_VARIANTES_ATIVAS = True     # False = volta a gerar sempre como na v54
_TITULO_INTELIGENTE = True   # True = Gemini (visao) acha a cabeca e o titulo desvia dela
_VARIANTES = ("frente", "sem_rosto", "perfil", "foto_real")
_DIRETRIZ_VARIANTE = {
    "frente": (
        "Subject: ONE adult person in a natural frontal or three-quarter view, soft directional window light "
        "that clearly and softly lights the face, gentle genuine expression, plain dark or softly blurred background."
    ),
    "perfil": (
        "Subject: ONE adult person in a calm side profile or three-quarter profile, looking toward a window, "
        "face clearly and softly lit by window light (not in deep shadow, not a silhouette), natural human proportions."
    ),
    "sem_rosto": (
        "Subject: ONE adult person seen from behind or in a distant wide shot looking out of a window, or only "
        "hands holding a cup near a window; the face is NOT visible. Soft window light, quiet contemplative "
        "atmosphere with gentle hope."
    ),
}


def _escolher_variante(seed, pedida=None):
    if pedida in _VARIANTES:
        return pedida
    return _VARIANTES[int(seed) % len(_VARIANTES)]


# ══════════════════════════════════════════════════════════════════════════════
# v61 — PROMPTS ENRIQUECIDOS: variação real a cada geração + leitura psicológica do tema
#  • cada estilo tem bancos de sujeito/composição/luz/superfície escolhidos pela seed
#  • Cinematic/Showcase/Automático ganham CONTEÚDO de cena: metáfora psicológica ligada ao tema
#    (ser visto, recomeço, vazio, tensão, vínculo, tristeza, identidade) + identidade "novo dia"
#  • só texto de prompt: sem custo extra de chamadas, memória ou processamento
# ══════════════════════════════════════════════════════════════════════════════
import unicodedata

_CHAVES_PSI = {
    "visto": ("vist", "ver ", "olhar", "olhad", "aparec", "atencao", "reconhec", "enxerg", "invisiv", "notad", "escut"),
    "recomeco": ("recome", "novo dia", "nova chance", "oportunid", "esperanc", "renasc", "mudanc", "amanhec",
                 "futuro", "chance", "supera", "cura", "transform"),
    "vazio": ("vazio", "solidao", "sozinh", "abandon", "carenc", "isolad"),
    "tensao": ("ansied", "raiva", "estress", "tensao", "panico", "irritab", "impuls", "crise", "intens", "explos"),
    "vinculo": ("relacion", "vinculo", "amor", "casal", "famili", "amizad", "afeto", "conex", "apego", "rejeic"),
    "tristeza": ("depress", "tristez", "luto", "perda", "dor ", "choro", "melanc"),
    "autoestima": ("autoestim", "identidade", "valor", "autocuid", "aceit", "proprio"),
}

_AMBIENTES_PSI = {
    "visto": (
        "a warm, lived-in consulting room at dawn: two armchairs angled toward each other, one of them softly lit "
        "by a shaft of morning light, a small wooden side table with a cup of tea and a closed notebook, sheer curtains glowing",
        "a quiet room where a single beam of early morning light crosses the floor and lands on one wooden chair, "
        "floating dust motes glowing in the beam, the rest of the room softly dark and calm",
        "a window at sunrise seen from inside a cozy room, sheer curtain glowing gold, a small plant on the sill, "
        "warm light spilling across the wooden floor toward the viewer",
        "a round mirror leaning against a wall catching the golden light of sunrise, reflecting only the window and the curtain",
        "a single warm lamp glowing on a wooden table in a softly blurred cool teal room, small but unmistakable, "
        "like being noticed in the dark",
    ),
    "recomeco": (
        "a wooden door slightly ajar in a calm room, bright sunrise light and soft sage plants at the threshold",
        "an open window on a quiet morning, curtains lifting gently, new light entering the room, a small sprouting "
        "plant in a clay pot on the sill",
        "a made bed with crisp linen at first light, a cup on the nightstand, a warm sun stripe across the covers",
        "a cozy reading corner with an armchair, a folded blanket and a window full of sunrise glow, an invitation to begin again",
        "a stone path leading through a garden gate toward soft sunrise light, dew on the leaves",
    ),
    "vazio": (
        "two armchairs facing each other, one empty with a folded blanket, warm morning light reaching the empty one",
        "a table set for two in a quiet room, one cup steaming, the opposite chair empty but touched by soft sunlight",
        "a quiet living room at golden hour with a lit lamp and a sunbeam over an empty sofa cushion",
        "a single warm window glowing in an otherwise softly dark room, a plant keeping company on the sill",
    ),
    "tensao": (
        "slow mist dissolving in a calm room where early light cuts through, tension easing, a plain wooden table",
        "raindrops on a window glass with a warm sunrise glow behind, the storm passing, a dry cozy sill with a plant",
        "a loosely coiled golden thread on a wooden table, untangling in soft light",
        "a steaming cup of tea on a windowsill, steam curling into the first light, calm after intensity",
    ),
    "vinculo": (
        "two ceramic cups side by side on a small table with morning steam, two chairs facing each other, warm light",
        "two armchairs close together with a shared blanket and warm sunrise light through the window",
        "a table with two sets of simple tableware and a small vase of sage leaves in warm morning light, welcoming and safe",
        "a worn wooden bench in a sunlit garden corner with two cushions, soft golden dawn light",
    ),
    "tristeza": (
        "gentle rain on a window with a thin line of warm golden light breaking through the clouds beyond, a quiet room, a cup of tea",
        "a softly lit room turning from night toward dawn, a blanket over an armchair, one warm lamp, the first light touching the curtains",
        "a plant leaning toward a sunlit window in a quiet room, new growth visible",
        "a wooden table with an open empty notebook and a pen near a window with early light, room to start writing again",
    ),
    "autoestima": (
        "a bright corner with an armchair, a plant and sunrise light forming a quiet spotlight on the seat",
        "a sunlit desk with a notebook, a cup and a small green plant, calm confidence, morning light",
        "a calm wall with a window reflecting the sunrise, a plant and warm light, quiet dignity",
    ),
    "novo_dia": (
        "a window at sunrise seen from inside a cozy room, sheer curtain glowing gold, a plant on the sill, light on the floor",
        "a wooden door slightly ajar with bright dawn light and sage plants at the threshold",
        "a warm lived-in consulting room at dawn, two armchairs, one softly lit by morning light, a cup of tea",
        "a quiet room with a single beam of early light landing on a wooden chair, dust motes glowing",
    ),
}

_LEITURA_PSI = {
    "visto": "the light should feel like being noticed, welcomed and safely witnessed",
    "recomeco": "a calm, hopeful sense of a new day, a new chance and a first step",
    "vazio": "an empty space that is not lonely but ready to be shared, with light finding it",
    "tensao": "tension easing, breath returning, calm after intensity",
    "vinculo": "safe connection, closeness without pressure, being held",
    "tristeza": "gentle comfort, light returning after the storm",
    "autoestima": "quiet dignity and self-worth, warmly lit",
    "novo_dia": "dawn as a metaphor for a new chance and a new opportunity",
}

_VAR = {
    "gold": {
        "sujeito": (
            "a wide matte teal-glazed chawan tea bowl", "a deep navy glazed cup with a delicate handle",
            "a shallow sage-green plate", "a tall narrow vase in petroleum teal", "a small round teapot in dusty navy",
            "a wide-mouthed pitcher in cream and teal", "a lidded jar with a deep teal glaze",
        ),
        "extra": (
            "fine hairline gold seams", "bold branching gold seams like rivers", "a single dramatic crack filled with gold",
            "scattered fragments joined by luminous gold",
        ),
        "onde": ("on dark slate", "on aged oak wood", "on rough linen cloth", "on pale stone", "on a dark walnut table",
                 "on a sage-green ceramic tile"),
        "comp": ("close-up on the seam with shallow depth of field", "three-quarter view at eye level",
                 "low angle with generous negative space", "soft top-down angle", "wide framing with the object small"),
        "luz": ("soft dawn side-light from the left", "warm window light with gentle shadow",
                "backlit rim light with a glowing edge", "diffused overcast light with warm glints on the gold"),
        "detalhe": ("a sprig of sage leaves nearby", "a folded neutral cloth", "a tiny wildflower", "a few fallen petals",
                    "nothing else, minimal"),
    },
    "smoke": {
        "sujeito": ("slow vertical ribbons of mist rising", "a gentle spiral of smoke unwinding",
                    "a soft curtain of mist drifting sideways", "thin wisps threading through a beam of light",
                    "low rolling mist at floor level with clear air above", "wisps curling around a window frame"),
        "luz": ("backlit by a warm solar-orange dawn glow", "side-lit teal light with an orange edge",
                "cold navy shadows opening to warm light at the top", "a single beam of golden light slicing through"),
        "onde": ("in a calm dark room", "in a quiet room with a large window", "against a soft gradient backdrop",
                 "over a wooden floor and a plain wall"),
        "comp": ("seen straight on", "from a slightly low angle", "wide with generous empty space",
                 "closer framing with soft depth"),
    },
    "portal": {
        "sujeito": ("a wooden door slightly ajar", "an arched doorway without a door", "a glass door with a sheer curtain",
                    "an open sliding wooden screen door", "a garden gate half open",
                    "a tall window opening onto a garden like a door"),
        "onde": ("from a quiet dark living room", "from a simple warm hallway", "from a cozy room with a rug and an armchair",
                 "from a stairwell landing"),
        "fora": ("a sunrise garden with sage plants", "a soft pastel sunrise sky above green hills",
                 "a stone path across dewy grass", "tall plants glowing in backlight"),
        "luz": ("golden-orange light flooding in", "long soft rays through dusty air", "gentle haze lit from behind"),
        "comp": ("seen straight on", "from a low angle", "from a gentle diagonal", "a wide shot with the ceiling visible"),
    },
    "ice": {
        "sujeito": ("a clear ice sphere melting on a sage leaf", "an ice cube on dark stone releasing a bright droplet",
                    "a fractured block of ice letting warm light through the crack",
                    "a long icicle with a bead of water about to fall", "a frosted window pane thawing in sunrise light",
                    "a small bowl carved of ice with a thin warm glow inside"),
        "luz": ("first warm solar-orange light refracting through the ice", "soft golden backlight inside the ice",
                "cool teal light with a warm point of orange"),
        "onde": ("on a dark wooden surface", "on a slate tile", "on a window sill", "on a smooth stone"),
        "comp": ("tabletop scale, macro-like", "eye level, shallow depth of field", "slightly from above"),
    },
    "floating": {
        "sujeito": ("a ceramic cup, a few leaves and a thin golden thread",
                    "a small key, a leaf and a golden thread (a new opportunity)",
                    "a few smooth pebbles in balance and a feather", "seeds drifting upward with a thin golden thread",
                    "an origami paper crane and a few sage leaves", "a small open book with lifting pages and floating leaves",
                    "three small paper lanterns with a warm glow", "a young plant sprig with a thin golden thread"),
        "comp": ("arranged in a vertical column", "along a gentle diagonal", "in a loose orbit around an empty center",
                 "rising from lower-left toward upper-right"),
        "fundo": ("a petroleum teal to navy gradient backdrop", "a sage to soft cream gradient with a warm glow",
                  "a deep navy backdrop with a subtle warm horizon glow", "a petroleum teal backdrop with a soft light bloom"),
    },
    "macro": {
        "sujeito": ("a dewdrop on a sage-green leaf vein", "a droplet on a spider web at sunrise", "a petal with a dew bead",
                    "a tiny sprout breaking through soil", "frost crystals melting on a leaf edge",
                    "moss with a glistening droplet", "a flower bud beginning to open", "a seed with a thin green shoot"),
        "bokeh": ("creamy teal bokeh with a single orange light point", "warm golden bokeh with cool navy edges",
                  "sage-green bokeh with white haze highlights"),
        "comp": ("razor-thin depth of field at eye level with the subject", "slightly from above",
                 "from a low angle, backlit"),
    },
    "museum": {
        "sujeito": ("a mended ceramic bowl on a low plinth", "a small sprouting plant in an old cup on a plinth",
                    "an empty gilded frame hanging alone under a spotlight",
                    "a simple wooden chair displayed like art under a spotlight", "a stack of smooth stones on a plinth",
                    "a gold-seamed vase on a plinth", "an open empty notebook on a lectern"),
        "parede": ("a deep navy wall", "a petroleum teal wall", "a soft sage wall with a warm spotlight",
                   "a warm off-white wall with a dark floor"),
        "luz": ("a single soft spotlight from above", "a skylight beam", "a side track light grazing the wall texture"),
    },
}

_TRATAMENTO = {
    "cinematic": (
        "35mm lens, shallow depth of field, blue hour turning to sunrise",
        "50mm lens, soft morning backlight through sheer curtains",
        "anamorphic look with a subtle warm flare, a quiet night turning to dawn",
        "85mm compression, window light, gentle haze",
    ),
    "showcase": (
        "soft diffused daylight, intimate and human scale, an editorial still-life feel",
        "a gentle window key light with warm fill, calm and refined",
        "a clean calm backdrop with a single symbolic element lit by morning light",
    ),
}

_ATMOSFERA = ("volumetric dust in the light", "light rain outside the window", "soft morning haze", "clean crisp air")

_REGRAS_PESSOA_DEPOIS = (
    "RULES: show a solid floor and a wall clearly; "
    "soft diffused light coming from the left or from the front, NEVER a sun disc, lamp, bright window or glare "
    "directly behind the right-hand area; no water, sea, lake or wet reflective floor; not an empty real-estate-style "
    "interior and not a long dark corridor; human scale with lived-in details; any object stays small and distant. "
    "EXPOSURE: bright, airy and luminous (mid-to-high key), a warm hopeful new-day morning mood, shadows lifted, "
    "no large pure-black areas, never gloomy or heavy. SCALE: realistic proportions seen from standing eye level "
    "(about 1.5 m camera height); furniture and objects stay in the left half and in the background, clearly smaller "
    "than a standing adult would be, and the right-hand foreground stays empty."
)

# v63: estilos abstratos (fundo desfocado/gradiente) nao tem chao/parede; regra propria
_ESTILOS_ABSTRATOS = ("macro", "floating", "ice")
_REGRAS_PESSOA_ABSTRATO = (
    "RULES: the backdrop is a smooth, soft, out-of-focus "
    "gradient or bokeh with gentle depth, no hard horizon lines and no busy detail; the symbolic element stays small "
    "and far from the right-hand area, which stays open and calmly lit; soft diffused light from the left or the "
    "front, NEVER a sun disc, lamp or glare directly behind the right-hand area. EXPOSURE: bright, airy and "
    "luminous (mid-to-high key), a warm hopeful new-day morning mood, no large pure-black areas, never gloomy or heavy."
)

# v63: o prompt do Automatico (main.py) sorteia agua; troca por equivalentes sem agua (so no modo Com Ronilson)
_SUBST_AGUA = (
    ("reflections on water at dawn", "warm reflections on a window glass at dawn"),
    ("dawn over still water and vegetation", "dawn light entering a calm room with plants"),
    ("still dawn landscape, open sky, slow water, breathing space, cool air",
     "a calm room with a wide window onto an open dawn sky, breathing space, cool air"),
    ("chrysalis of light: leaves, water reflection, dawn, growth",
     "chrysalis of light: leaves, a glass jar catching dawn light, growth"),
    # v64: o espaco "reservado para uma pessoa" induz o Gemini a desenhar um vulto; folhagem/escuro conflitam com a identidade
    ("reserved for compositing a real person later", "kept plain and calm, with nothing in it"),
    ("sunbeam through leaves", "a soft sunbeam through sheer curtains"),
    ("stays darker/muted so typography can sit there", "stays calm and slightly deeper in tone so typography can sit there"),
    ("soft overcast light through trees, mist, hope at the edge of the frame, not gloomy",
     "soft overcast morning light through a window, gentle haze, hope at the edge of the frame, not gloomy"),
)


def _sem_agua(txt):
    for a, b in _SUBST_AGUA:
        txt = txt.replace(a, b)
    return txt


def _norm_psi(t):
    t = unicodedata.normalize("NFKD", t or "").encode("ascii", "ignore").decode("ascii").lower()
    return " " + t.replace("*", " ").replace("-", " ").replace(":", " ") + " "


def _grupo_psi(tema, rnd):
    t = _norm_psi(tema)
    grupos = [g for g, chaves in _CHAVES_PSI.items() if any(c in t for c in chaves)]
    return rnd.choice(grupos) if grupos else "novo_dia"


# v69: cadeiras/poltronas saiam demais e o fundo ficava gigante ao lado da pessoa (escala errada)
_MOVEIS_GRANDES = ("chair", "armchair", "sofa", "bench", "stool")
_REGRA_ESCALA_V69 = (
    "NO chairs, armchairs, stools, benches or sofas anywhere in the frame, and no large furniture: the environment "
    "is architectural (wall, floor, soft window light, gentle shadows) with at most one small plant or cup far in "
    "the background. WIDE SHOT with a distant camera: everything in the scene looks small and far away, windows "
    "and doors are modest in size (never a huge floor-to-ceiling feature filling the frame), so a standing adult "
    "placed in the foreground will be clearly larger than any object in the scene."
)


def _enriquecer(estilo, tema, seed, sem_pessoas=False):
    """Texto extra do prompt: cena específica desta geração + leitura psicológica do tema."""
    try:
        rnd = random.Random(int(seed) * 7919 + sum(ord(c) for c in estilo))
        esc = lambda lista: lista[rnd.randrange(len(lista))]
        grupo = _grupo_psi(tema, rnd)
        partes = []

        if estilo in ("cinematic", "showcase", "auto"):
            opcoes_amb = _AMBIENTES_PSI[grupo]
            if sem_pessoas:  # v69: no Com Ronilson, ambientes com cadeira/poltrona/sofa ficam de fora
                opcoes_amb = [o for o in opcoes_amb if not any(k in o for k in _MOVEIS_GRANDES)] or opcoes_amb
            partes.append(f"Setting (a psychological metaphor, never literal): {esc(opcoes_amb)}.")
            if estilo in _TRATAMENTO:
                partes.append(f"Treatment: {esc(_TRATAMENTO[estilo])}; {esc(_ATMOSFERA)}.")
            if estilo == "showcase":
                partes.append("Not an advertising or real-estate look: intimate, human, quiet.")
            partes.append("No sea, lake, beach or tourist-landscape imagery.")
        elif estilo in _VAR:
            v = _VAR[estilo]
            if estilo == "gold":
                partes.append(f"Specific scene (this takes priority over the generic description): {esc(v['sujeito'])}, "
                              f"kintsugi-mended with {esc(v['extra'])}, {esc(v['onde'])}; {esc(v['comp'])}; "
                              f"{esc(v['luz'])}; {esc(v['detalhe'])}.")
            elif estilo == "smoke":
                partes.append(f"Specific scene (this takes priority over the generic description): {esc(v['sujeito'])} "
                              f"{esc(v['onde'])}; {esc(v['luz'])}; {esc(v['comp'])}.")
            elif estilo == "portal":
                partes.append(f"Specific scene (this takes priority over the generic description): {esc(v['sujeito'])} seen "
                              f"{esc(v['onde'])}, with {esc(v['fora'])} outside; {esc(v['luz'])}; {esc(v['comp'])}.")
            elif estilo == "ice":
                partes.append(f"Specific scene (this takes priority over the generic description): {esc(v['sujeito'])} "
                              f"{esc(v['onde'])}; {esc(v['luz'])}; {esc(v['comp'])}; small tabletop scale only, no large bodies of water.")
            elif estilo == "floating":
                partes.append(f"Specific scene (this takes priority over the generic description): {esc(v['sujeito'])}, "
                              f"{esc(v['comp'])}, on {esc(v['fundo'])}.")
            elif estilo == "macro":
                partes.append(f"Specific scene (this takes priority over the generic description): macro of "
                              f"{esc(v['sujeito'])}; {esc(v['comp'])}; {esc(v['bokeh'])}.")
            elif estilo == "museum":
                partes.append(f"Specific scene (this takes priority over the generic description): {esc(v['sujeito'])}; "
                              f"{esc(v['parede'])}; {esc(v['luz'])}.")

        partes.append(f"Emotional reading of the image: {_LEITURA_PSI[grupo]}.")
        partes.append(f"Make this image clearly different from other generations of the same style (variation {int(seed) % 997}); "
                      "avoid the most obvious, stock-photo composition.")
        if sem_pessoas:
            partes.append("The scene is EMPTY of people: no figures, faces, hands, silhouettes, ghostly or blurred "
                          "human shapes, reflections of people, statues, mannequins or portraits anywhere, "
                          "especially not in the right-hand area.")
            partes.append(_REGRAS_PESSOA_ABSTRATO if estilo in _ESTILOS_ABSTRATOS else _REGRAS_PESSOA_DEPOIS)
            partes.append(_REGRA_ESCALA_V69)  # v69
        return " ".join(partes)
    except Exception as e:
        print(f"[estilo] enriquecimento ignorado: {e}")
        return ""


def _prompt(estilo, tema="", variante=None, seed=None):
    e = ESTILOS[estilo]
    M = _m()
    tema_limpo = (
        M._texto_tema_limpo(tema)
        if (M and hasattr(M, "_texto_tema_limpo"))
        else (tema or "").replace("*", " ").replace(":", " ").replace("-", " ").strip()
    )
    contexto_tema = f' Concept / emotional theme of this post: "{tema_limpo}". ' if tema_limpo else " "

    composicao = (
        "Vertical 4:5 Instagram portrait composition. Keep the UPPER-LEFT third calm, darker and "
        "free of busy detail for large typography; place the main subject in the lower "
        "two thirds, slightly right of center, with generous negative space and clear visual depth."
    )

    realismo = ""
    if _REALISMO_SUAVE and estilo in _ESTILOS_COM_PESSOA:
        realismo = _TOQUE_REALISMO + " "
    diretriz = (_DIRETRIZ_VARIANTE.get(variante, "") + " ") if variante else ""
    enriq = (_enriquecer(estilo, tema, seed) + " ") if seed is not None else ""  # v61

    return (
        "Photorealistic editorial photograph for AlvoreSer, a Brazilian psychology clinic "
        "whose identity is dawn, hope, emotional care, healing and transformation. "
        f"{contexto_tema}"
        f"Visual style and scene: {e['cena']}. Lighting: {e['luz']}. "
        f"{enriq}"
        "Color palette strictly harmonious with clinic identity: deep navy #024059, petroleum teal #1B797D, "
        "soft sage #779993, solar orange #F9AB0B as accent light only, snow white haze #F4F6F8. "
        "Mood: professional, welcoming, intimate, never clinical-cold, never hospital, "
        f"elevated realism, authentic photographic texture. {composicao} {realismo}{diretriz}"
        "No text, no letters, no typography, no words, no logos, no watermark, no borders, "
        "no artificial 3D look, no deformed elements, no extra limbs, high definition, authentic photography."
    )


# ── IA de imagem: Gemini -> Cloudflare (opcional) ─────────────────────────────
_GEMINI_IMAGE_EXTRA = (
    "gemini-3.5-flash",
    "gemini-3.5-flash-preview",
    "gemini-3.0-flash",
    "gemini-3.1-flash-image",
    "gemini-3.1-flash-image-preview",
    "gemini-2.5-flash-image",
    "gemini-2.5-flash",
)


def _gerar_imagem_ia(prompt):
    """Retorna (imagem_PIL, None) ou (None, motivo legivel)."""
    M = _m()
    erros = []

    chave = getattr(M, "GEMINI_API_KEY", None)
    if not chave:
        erros.append("GEMINI_API_KEY nao configurada")
    else:
        payload = {
            "contents": [{"parts": [{"text": prompt}]}],
            "generationConfig": {
                "responseModalities": ["TEXT", "IMAGE"],
                "imageConfig": {"aspectRatio": "4:5"},
            },
        }
        modelos_usados = list(getattr(M, "GEMINI_IMAGE_MODELOS", ()))
        for extra in _GEMINI_IMAGE_EXTRA:
            if extra not in modelos_usados:
                modelos_usados.append(extra)
        for modelo in modelos_usados:
            try:
                url = (
                    f"https://generativelanguage.googleapis.com/v1beta/models/"
                    f"{modelo}:generateContent?key={chave}"
                )
                r = requests.post(url, json=payload, timeout=60)
                if r.status_code >= 400:
                    print(f"[estilo] {modelo} HTTP {r.status_code}: {r.text[:200]}")
                    dica = {
                        429: "sem cota — confira plano/faturamento da chave Gemini",
                        404: "modelo nao existe para esta chave",
                        403: "chave sem permissao",
                    }.get(r.status_code, "requisicao recusada")
                    erros.append(f"{modelo}: HTTP {r.status_code} ({dica})")
                    continue
                raw = M._bytes_imagem_gemini(r.json())
                if not raw:
                    erros.append(f"{modelo}: respondeu sem imagem")
                    continue
                print(f"[estilo] imagem ok via Gemini {modelo}")
                return M._fit_canvas(Image.open(io.BytesIO(raw))), None
            except Exception as e:
                print(f"[estilo] {modelo} falhou: {e}")
                erros.append(f"{modelo}: {str(e)[:80]}")

    conta = os.getenv("CLOUDFLARE_ACCOUNT_ID")
    token = os.getenv("CLOUDFLARE_API_TOKEN")
    if conta and token:
        try:
            url = (
                f"https://api.cloudflare.com/client/v4/accounts/{conta}"
                "/ai/run/@cf/black-forest-labs/flux-1-schnell"
            )
            r = requests.post(
                url,
                headers={"Authorization": f"Bearer {token}"},
                json={"prompt": prompt[:2000], "steps": 6},
                timeout=70,
            )
            if r.status_code >= 400:
                print(f"[estilo] cloudflare HTTP {r.status_code}: {r.text[:200]}")
                erros.append(f"Cloudflare: HTTP {r.status_code}")
            else:
                b64 = (r.json().get("result") or {}).get("image")
                if b64:
                    print("[estilo] imagem ok via Cloudflare FLUX.1 schnell")
                    return M._fit_canvas(Image.open(io.BytesIO(base64.b64decode(b64)))), None
                erros.append("Cloudflare: respondeu sem imagem")
        except Exception as e:
            print(f"[estilo] cloudflare falhou: {e}")
            erros.append(f"Cloudflare: {str(e)[:80]}")
    else:
        erros.append("Cloudflare nao configurado")

    return None, " | ".join(erros)


# ── Montagem da imagem-base do estilo ─────────────────────────────────────────
# v55b: libera o topo para o título quando o rosto está alto demais (não mexe no rosto)
_W, _H = 1080, 1350
_DY_MAX = int(_H * 0.30)           # desloca no máximo ~405px
_ALVO_TOPO_ROSTO = int(_H * 0.40)  # topo da folga do rosto (como o motor mede) deve ficar abaixo disto
_cascata_rosto = None


def _medir_rosto(img):
    """(x, y, w, h) do maior rosto frontal (Haar) ou None."""
    global _cascata_rosto
    try:
        import cv2
        if _cascata_rosto is None:
            _cascata_rosto = cv2.CascadeClassifier(
                cv2.data.haarcascades + "haarcascade_frontalface_default.xml")
        arr = np.array(img.convert("L"))
        lado = int(_W * 0.08)
        for sf, mn in ((1.1, 5), (1.05, 4), (1.05, 3)):
            faces = _cascata_rosto.detectMultiScale(
                arr, scaleFactor=sf, minNeighbors=mn, minSize=(lado, lado))
            faces = [f for f in faces if f[1] + f[3] / 2 < _H * 0.80]
            if len(faces):
                fx, fy, fw, fh = max(faces, key=lambda f: f[2] * f[3])
                print(f"[estilo] rosto detectado: x={fx} y={fy} w={fw} h={fh}")
                return int(fx), int(fy), int(fw), int(fh)
    except Exception as e:
        print(f"[estilo] deteccao de rosto falhou: {e}")
    return None


def _dy_necessario(rosto):
    """Quantos px a cena precisa descer para o título caber acima do rosto.
    O motor de título protege o rosto com folga de 0.55*altura acima dele."""
    if rosto is None:
        return 0
    _, fy, _, fh = rosto
    return max(0, _ALVO_TOPO_ROSTO - (fy - int(fh * 0.55)))


def _abrir_espaco_topo(img, dy):
    """Desloca a cena para baixo em dy px; o topo é estendido espelhando e
    desfocando as linhas de cima (fundo escuro fora de foco)."""
    a = np.asarray(img.convert("RGB"))
    n = min(dy, 220)
    ext = np.pad(a[:n], ((dy, 0), (0, 0), (0, 0)), mode="reflect")[:dy]
    cheio = np.concatenate([ext, a], axis=0)
    borrado = np.asarray(
        Image.fromarray(cheio).filter(ImageFilter.GaussianBlur(20))).astype(np.float32)
    cheio = cheio.astype(np.float32)
    feather = 70
    m = np.zeros((cheio.shape[0], 1, 1), dtype=np.float32)
    m[:dy] = 1.0
    m[dy:dy + feather, 0, 0] = np.linspace(1.0, 0.0, feather)
    out = cheio * (1 - m) + borrado * m
    return Image.fromarray(np.clip(out, 0, 255).astype(np.uint8)).crop((0, 0, _W, _H))


# v55c: foto real do banco (Cloudinary) com tratamento leve por estilo
def _grade_estilo(img, estilo):
    a = np.asarray(img.convert("RGB"), dtype=np.float32) / 255.0
    lum = a.mean(axis=2, keepdims=True)
    if estilo == "cinematic":
        # sombras levemente azul-petroleo, altas-luzes levemente quentes, contraste suave
        a = a + np.array([0.00, 0.03, 0.05], dtype=np.float32) * (1 - lum) \
              + np.array([0.04, 0.02, -0.02], dtype=np.float32) * lum
        a = (a - 0.5) * 1.08 + 0.5
        forca = 0.38
    else:
        a = (a - 0.5) * 1.04 + 0.5
        forca = 0.22
    h, w = a.shape[:2]
    yy, xx = np.mgrid[0:h, 0:w].astype(np.float32)
    d = np.sqrt(((xx - w / 2) / (w / 2)) ** 2 + ((yy - h * 0.45) / (h * 0.62)) ** 2)
    v = 1 - forca * np.clip(d - 0.55, 0, 1) ** 1.6
    a = a * v[..., None]
    return Image.fromarray((np.clip(a, 0, 1) * 255).astype(np.uint8))


def _foto_real_do_banco(estilo, tema):
    """Foto real do banco de imagens + tratamento. Retorna imagem PIL ou None."""
    M = _m()
    try:
        url, pid = M.buscar_imagem(tema)
        if not url:
            return None
        r = requests.get(url, timeout=25)
        r.raise_for_status()
        img = M._fit_canvas(Image.open(io.BytesIO(r.content)))
        print(f"[estilo] foto real do banco: {pid}")
        return _grade_estilo(img, estilo)
    except Exception as e:
        print(f"[estilo] foto real indisponivel: {e}")
        return None


# v55c: o Gemini (visao) diz onde esta a cabeca, inclusive de perfil, de costas ou em silhueta
def _cabeca_por_visao(img):
    """(x0, y0, x1, y1) em px do canvas, ou None se nao ha cabeca visivel / falhou."""
    M = _m()
    chave = getattr(M, "GEMINI_API_KEY", None)
    if not chave:
        return None
    mini = img.convert("RGB").resize((432, 540), Image.Resampling.LANCZOS)
    buf = io.BytesIO()
    mini.save(buf, format="JPEG", quality=85)
    pergunta = (
        'Look at this image. If a person is visible, answer ONLY with JSON {"cabeca":[ymin,xmin,ymax,xmax]} '
        "giving the bounding box of the person's HEAD (top of the hair to the chin, also for a profile or the "
        "back of the head), coordinates normalized 0-1000. If no head is visible answer {\"cabeca\":null}."
    )
    payload = {
        "contents": [{"parts": [
            {"inlineData": {"mimeType": "image/jpeg", "data": base64.b64encode(buf.getvalue()).decode()}},
            {"text": pergunta},
        ]}],
        "generationConfig": {"responseMimeType": "application/json", "temperature": 0},
    }
    for modelo in ("gemini-2.5-flash", "gemini-3.5-flash"):
        try:
            url = (f"https://generativelanguage.googleapis.com/v1beta/models/"
                   f"{modelo}:generateContent?key={chave}")
            r = requests.post(url, json=payload, timeout=25)
            if r.status_code >= 400:
                print(f"[cabeca] {modelo} HTTP {r.status_code}")
                continue
            partes = r.json()["candidates"][0]["content"]["parts"]
            txt = "".join(p.get("text", "") for p in partes if not p.get("thought"))
            txt = txt.replace("```json", "").replace("```", "").strip()
            caixa = json.loads(txt).get("cabeca")
            if not caixa:
                print(f"[cabeca] {modelo}: sem cabeca visivel")
                return None
            ymin, xmin, ymax, xmax = [max(0.0, min(1000.0, float(v))) for v in caixa]
            if ymax <= ymin or xmax <= xmin:
                continue
            bbox = (int(xmin / 1000 * _W), int(ymin / 1000 * _H),
                    int(xmax / 1000 * _W), int(ymax / 1000 * _H))
            print(f"[cabeca] {modelo}: cabeca em {bbox}")
            return bbox
        except Exception as e:
            print(f"[cabeca] {modelo} falhou: {e}")
    return None


def _card_titulo_inteligente(M, base, tema, seed):
    """Mesmo motor de titulo do gerar_card_imagem, mas com a cabeca real (perfil incluso)."""
    cabeca = _cabeca_por_visao(base)
    cor1 = M.MARINHO
    try:
        cor1, _ = M.cores_fundo(base.convert("RGB").resize((120, 150), Image.Resampling.LANCZOS))
    except Exception as e:
        print(f"[estilo] cores_fundo falhou: {e}")
    img = M.tratar_foto_editorial(base.convert("RGB"), cor1, seed)
    cor_dest, cor_fundo_txt = M._escolher_cor_destaque(seed)
    out, _ = M.desenhar_titulo(img, tema, seed, cor_dest=cor_dest, cor_fundo_txt=cor_fundo_txt,
                               cor_overlay=None, tem_pessoa=False, em_pe=True,
                               cabeca_bbox=cabeca)
    return out


def _base_cena(estilo, seed, tema="", variante_pedida=None):
    M = _m()
    variante = None
    if _VARIANTES_ATIVAS and estilo in _ESTILOS_COM_PESSOA:
        variante = _escolher_variante(seed, variante_pedida)
        print(f"[estilo] variante da cena: {variante}")
        if variante == "foto_real":
            real = _foto_real_do_banco(estilo, tema)
            if real is not None:
                _ETAPA["variante"] = variante
                return real, None
            print("[estilo] sem foto real; usando rosto de frente por IA")
            variante = "frente"
    _ETAPA["variante"] = variante or "-"
    prompt = _prompt(estilo, tema, variante, seed)
    print(f"[estilo] Gerando imagem IA para '{estilo}'...")
    img, motivo = _gerar_imagem_ia(prompt)
    aviso = None
    if img is None:
        print(f"[estilo] Falha na imagem IA ({motivo}), usando gradiente da paleta")
        img = M._gerar_fundo_gradiente(M.MARINHO, M.PETROLEO, seed)
        aviso = f"A imagem por IA falhou ({motivo}); usei o gradiente da paleta."

    # v55b: Cinematic/Showcase — só desloca a cena p/ liberar o topo (rosto não é alterado)
    if _AJUSTE_POSICAO_TEXTO and img is not None and aviso is None and estilo in _ESTILOS_COM_PESSOA:
        try:
            rosto = _medir_rosto(img)
            dy = min(_dy_necessario(rosto), _DY_MAX)
            if rosto is not None and dy > 12:
                print(f"[estilo] abrindo {dy}px de espaco livre no topo para o titulo")
                img = _abrir_espaco_topo(img, dy)
        except Exception as e:
            print(f"[estilo] ajuste de posicao falhou (ignorado): {e}")
    return img, aviso


# ── Rota ──────────────────────────────────────────────────────────────────────
# ══════════════════════════════════════════════════════════════════════════════
# v57 — "Com Ronilson": recorte SEM FUNDO (pasta Cloudinary ronilson_sem_fundo)
# integrado a um cenário criado conforme tema + paleta + estilo escolhido.
# Só adiciona: nada do fluxo dos outros estilos é alterado (ativado por com_ronilson=True).
# Não usa rembg (o recorte já vem pronto) -> leve para os 512MB do Render.
# ══════════════════════════════════════════════════════════════════════════════
_PREFIXOS_SEM_FUNDO = (
    "Banco de Imagens/Ronilson_sem_fundo",
    "Banco de Imagens/ronilson_sem_fundo",
    "Banco de Imagens/Ronilson_Sem_Fundo",
    "banco de imagens/ronilson_sem_fundo",
    "Ronilson_sem_fundo",
    "ronilson_sem_fundo",
)
_cache_recortes = {"t": 0.0, "lista": []}

# desfoque do cenário (profundidade de campo) por estilo
_BLUR_CENARIO = {
    "cinematic": 3.2, "showcase": 2.0, "macro": 4.0, "auto": 1.8,
    "gold": 2.4, "smoke": 2.2, "portal": 2.4, "ice": 2.2, "floating": 1.8, "museum": 2.0,
}


def _listar_recortes_ronilson():
    """Lista (com cache de 10 min) os recortes PNG/WebP da pasta ronilson_sem_fundo."""
    import cloudinary.api
    M = _m()
    if _cache_recortes["lista"] and time.time() - _cache_recortes["t"] < 600:
        return _cache_recortes["lista"]

    def _ok(r):
        pid = r.get("public_id", "")
        return (
            M.CLOUDINARY_POSTS not in pid
            and M.CLOUDINARY_PREVIEW not in pid
            and (r.get("format") or "png").lower() in ("png", "webp", "avif", "tiff", "tif")
        )

    achados = []
    for pref in _PREFIXOS_SEM_FUNDO:
        cursor = None
        for _ in range(5):
            kw = dict(type="upload", prefix=pref + "/", max_results=100)
            if cursor:
                kw["next_cursor"] = cursor
            try:
                res = cloudinary.api.resources(**kw)
            except Exception as e:
                print(f"[ronilson] '{pref}': {e}")
                break
            achados += [r for r in res.get("resources", []) if _ok(r)]
            cursor = res.get("next_cursor")
            if not cursor:
                break
        if achados:
            print(f"[ronilson] {len(achados)} recortes em '{pref}'")
            break

    if not achados:  # varredura geral (caso a pasta tenha outro caminho/caixa)
        cursor = None
        for _ in range(10):
            kw = dict(type="upload", max_results=500)
            if cursor:
                kw["next_cursor"] = cursor
            try:
                res = cloudinary.api.resources(**kw)
            except Exception as e:
                print(f"[ronilson] varredura geral: {e}")
                break
            achados += [
                r for r in res.get("resources", [])
                if _ok(r) and "sem_fundo" in r.get("public_id", "").lower().replace(" ", "_")
            ]
            cursor = res.get("next_cursor")
            if not cursor:
                break

    if achados:
        _cache_recortes.update(t=time.time(), lista=achados)
    return achados


def _carregar_recorte_ronilson():
    """Sorteia (baralho, sem repetir) um recorte e devolve (imagem RGBA, public_id)."""
    M = _m()
    recursos = _listar_recortes_ronilson()
    if not recursos:
        raise ErroEstilo(
            "Nao encontrei imagens na pasta ronilson_sem_fundo do Cloudinary "
            "(PNG/WebP com transparencia)."
        )
    r = M._proxima_foto_baralho("ronilson_sem_fundo", recursos)
    url, pid = r.get("secure_url"), r.get("public_id", "")
    resp = requests.get(url, timeout=30)
    resp.raise_for_status()
    img = Image.open(io.BytesIO(resp.content))
    if img.mode in ("RGBA", "LA") or (img.mode == "P" and "transparency" in img.info):
        img = img.convert("RGBA")
    else:
        raise ErroEstilo(f"A imagem {pid} nao tem transparencia (fundo removido).")
    lado = max(img.size)
    if lado > 2000:  # economiza memoria
        f = 2000 / lado
        img = img.resize((int(img.width * f), int(img.height * f)), Image.Resampling.LANCZOS)
    print(f"[ronilson] recorte: {pid} {img.size}")
    return img, pid


# ── Cenário (sem pessoas) conforme tema + paleta + estilo ─────────────────────
def _prompt_cenario_ronilson(estilo, tema, seed):
    M = _m()
    if estilo == "auto":
        return (
            _sem_agua(M._prompt_fundo_ia(tema, seed, True))
            + " The scene needs a believable floor or ground plane and clear depth; keep the right side plain, "
              "calm and empty; soft key light from the upper left. "
            + _enriquecer("auto", tema, seed, sem_pessoas=True)  # v61
        )
    e = ESTILOS[estilo]
    tema_limpo = M._texto_tema_limpo(tema) if hasattr(M, "_texto_tema_limpo") else (tema or "")
    contexto = f' Concept / emotional theme of this post: "{tema_limpo}". ' if tema_limpo else " "
    return (
        "Photorealistic editorial photograph of an EMPTY environment (no people) for AlvoreSer, a Brazilian "
        "psychology clinic whose identity is dawn, hope, emotional care, healing and transformation."
        f"{contexto}"
        f"Visual style and scene: {e['cena']}. Lighting: {e['luz']}. "
        f"{_enriquecer(estilo, tema, seed, sem_pessoas=True)} "
        "Color palette strictly harmonious with clinic identity: deep navy #024059, petroleum teal #1B797D, "
        "soft sage #779993, solar orange #F9AB0B as accent light only, snow white haze #F4F6F8. "
        f"Composition: vertical 4:5, {'a soft out-of-focus backdrop with clear visual depth' if estilo in _ESTILOS_ABSTRATOS else 'a believable floor or ground plane and clear visual depth'}. The RIGHT 55% "
        "of the frame is plain, calm and softly lit (wall, air, bokeh or empty floor) with nothing in it; "
        "keep the LEFT 40% calm and uncluttered for large typography. "
        "Any symbolic object sits low, small, in the lower-left or center, below the typography area. "
        "Soft key light coming from the upper left. "
        "Absolutely no people, no faces, no hands, no mannequins, no silhouettes, no text, no letters, "
        "no logos, no watermark, no borders, high definition, authentic photographic texture."
    )


def _cenario_ronilson(estilo, tema, seed):
    M = _m()
    img, motivo = _gerar_imagem_ia(_prompt_cenario_ronilson(estilo, tema, seed))
    aviso = None
    if img is None:
        print(f"[ronilson] cenario IA falhou ({motivo}); gradiente da paleta")
        img = M._gerar_fundo_gradiente(M.MARINHO, M.PETROLEO, seed)
        aviso = f"O cenario por IA falhou ({motivo}); usei o gradiente da paleta."
    return img, aviso


# ── Integração: o Ronilson passa a fazer parte da luz e da sombra da cena ────
def _limpar_borda_recorte(rgba):
    """Tira a franja clara do recorte: encolhe 1px o alpha e repinta a borda com a cor de dentro."""
    import cv2
    a = np.asarray(rgba.split()[3]).astype(np.float32) / 255.0
    rgb = np.asarray(rgba.convert("RGB")).astype(np.float32)
    a = np.clip((a - 0.10) / 0.80, 0, 1)
    nucleo = cv2.erode(a, cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (7, 7)))
    num = cv2.GaussianBlur(rgb * nucleo[..., None], (0, 0), 4)
    den = cv2.GaussianBlur(nucleo, (0, 0), 4)[..., None]
    sangra = num / np.maximum(den, 1e-3)
    w = np.clip(1.0 - nucleo, 0, 1)[..., None] * (den > 0.05)
    rgb = rgb * (1 - w) + sangra * w
    a = cv2.GaussianBlur(cv2.erode(a, np.ones((3, 3), np.uint8)), (0, 0), 0.7)
    return rgb, a


def _caixa_cabeca(a_f):
    """Zona da cabeça (heurística do salto de largura dos ombros, igual à compor_pessoa)."""
    try:
        m = a_f > 0.04
        linhas = np.where(m.any(axis=1))[0]
        if len(linhas) == 0:
            return None
        larg = np.zeros(m.shape[0], dtype=np.int32)
        for r in linhas:
            cols = np.where(m[r])[0]
            larg[r] = cols.max() - cols.min()
        y_topo = int(linhas[0])
        jan = larg[y_topo: y_topo + max(10, int(_H * 0.05))]
        ref = float(np.median(jan[jan > 0])) if np.any(jan > 0) else 0.0
        y_fim = y_topo + int(_H * 0.30)
        if ref > 0:
            for r in range(y_topo, min(m.shape[0], y_topo + int(_H * 0.55))):
                if larg[r] > ref * 1.5:
                    y_fim = r + int(_H * 0.08)
                    break
        cols = np.where(m[y_topo:y_fim].any(axis=0))[0]
        if len(cols) == 0:
            return None
        return (max(0, int(cols.min()) - 25), max(0, y_topo - 15),
                min(_W, int(cols.max()) + 25), min(_H, y_fim + 25))
    except Exception as e:
        print(f"[ronilson] caixa da cabeca falhou: {e}")
        return None


def _integrar_ronilson(fundo, recorte, estilo, seed):
    """Retorna (imagem RGB, corpo_inteiro, caixa_da_cabeca)."""
    import cv2
    rgb_r, a_r = _limpar_borda_recorte(recorte)
    ys, xs = np.where(a_r > 0.04)
    if len(ys) == 0:
        raise ErroEstilo("O recorte do Ronilson veio vazio.")
    x_a, x_b, y_a, y_b = xs.min(), xs.max() + 1, ys.min(), ys.max() + 1
    rgb_r, a_r = rgb_r[y_a:y_b, x_a:x_b], a_r[y_a:y_b, x_a:x_b]
    ph, pw = a_r.shape
    prop = ph / pw

    # tamanho/posição: corpo inteiro pisa no chão; busto/meio corpo é cortado pela base do card
    corpo = prop >= 2.2
    if corpo:
        alt = int(_H * 0.80)
    else:
        larg_alvo = int(_W * (0.52 if prop >= 1.35 else 0.58))
        alt = min(int(larg_alvo * prop), int(_H * 1.0))
    nw = max(1, int(alt / prop))
    rgb_s = cv2.resize(rgb_r, (nw, alt), interpolation=cv2.INTER_AREA)
    a_s = cv2.resize(a_r, (nw, alt), interpolation=cv2.INTER_AREA)
    x0 = max(int(_W * 0.42), _W - nw - int(_W * 0.03))
    y0 = int(_H * 0.975) - alt if corpo else _H - alt

    sub = np.zeros((_H, _W, 3), np.float32)
    a_f = np.zeros((_H, _W), np.float32)
    sx0, sy0 = max(0, -x0), max(0, -y0)
    dx0, dy0 = max(0, x0), max(0, y0)
    cw, ch = min(nw - sx0, _W - dx0), min(alt - sy0, _H - dy0)
    sub[dy0:dy0 + ch, dx0:dx0 + cw] = rgb_s[sy0:sy0 + ch, sx0:sx0 + cw]
    a_f[dy0:dy0 + ch, dx0:dx0 + cw] = a_s[sy0:sy0 + ch, sx0:sx0 + cw]

    # cenário com profundidade de campo
    fundo = fundo.convert("RGB").resize((_W, _H), Image.Resampling.LANCZOS)
    fundo = fundo.filter(ImageFilter.GaussianBlur(_BLUR_CENARIO.get(estilo, 2.0)))
    bg = np.asarray(fundo).astype(np.float32)

    # direção da luz: lado mais claro do cenário
    lum = bg.mean(axis=2)
    luz_x = -1.0 if lum[:, : _W // 2].mean() >= lum[:, _W // 2:].mean() * 0.95 else 1.0

    # cor/luz ambiente em volta dele
    solido = (a_f > 0.5).astype(np.uint8)
    anel = cv2.dilate(solido, np.ones((41, 41), np.uint8)) - solido
    amb = bg[anel > 0].mean(axis=0) if anel.any() else bg.reshape(-1, 3).mean(axis=0)

    # 1) ajusta cor e exposição do Ronilson à cena (sem pintar a pele)
    media = sub[solido > 0].mean(axis=0)
    ganho = (amb / max(amb.mean(), 1)) / (media / max(media.mean(), 1))
    ganho = np.clip(1 + 0.30 * (ganho - 1), 0.80, 1.20)
    expo = float(np.clip((amb.mean() + 55) / (media.mean() + 55), 0.62, 1.08))
    sub = sub * ganho * (expo ** 0.65)

    # 2) luz direcional na pessoa: lado da luz mais claro, lado oposto mais escuro
    X = np.linspace(0, 1, _W, dtype=np.float32)[None, :]
    t = np.clip((X - x0 / _W) / max(nw / _W, 1e-3), 0, 1)
    t = t if luz_x > 0 else 1 - t  # t=0 no lado da luz
    sub *= (1.06 - 0.16 * t)[..., None]
    sub *= (1.0 - 0.06 * np.linspace(0, 1, _H, dtype=np.float32))[:, None, None]

    # 3) light wrap + contorno de luz na borda
    bg_suave = cv2.GaussianBlur(bg, (0, 0), 20)
    nucleo = cv2.GaussianBlur(cv2.erode(a_f, np.ones((13, 13), np.uint8)), (0, 0), 3)
    borda = np.clip(a_f - nucleo, 0, 1)[..., None]
    sub = sub * (1 - 0.38 * borda) + bg_suave * 1.08 * 0.38 * borda
    lado = np.clip(1 - np.abs(t - 0.0) * 2.0, 0, 1)[..., None]
    rim = np.array([255, 205, 130], np.float32) * 0.5 + amb * 0.6
    sub = sub + 0.28 * borda * lado * rim * (1 - sub / 255.0)

    # 4) sombras no cenário: projetada + de contato no chão
    sil = cv2.GaussianBlur(a_f, (0, 0), 26)
    desloc = np.float32([[1, 0, -luz_x * 34], [0, 1, 14]])
    sombra = cv2.warpAffine(sil, desloc, (_W, _H))
    if corpo:
        base_y = int(y0 + alt - 4)
        fx = np.where(a_f[max(0, base_y - 40):min(_H, base_y), :].max(axis=0) > 0.3)[0]
        cx = int(fx.mean()) if len(fx) else x0 + nw // 2
        chao = np.zeros((_H, _W), np.float32)
        cv2.ellipse(chao, (cx, base_y), (int(nw * 0.62), int(_H * 0.016) + 6), 0, 0, 360, 1.0, -1)
        chao = cv2.GaussianBlur(chao, (0, 0), 14)
        sombra = np.clip(sombra + 0.9 * chao, 0, 1)
        degrade = np.clip((np.arange(_H, dtype=np.float32) - (base_y - 30)) / 160.0, 0, 1)
        bg = bg * (1 - 0.22 * degrade)[:, None, None]
    cor_sombra = amb * 0.20
    s = (0.50 * sombra)[..., None]
    bg = bg * (1 - s) + cor_sombra * s

    # 5) composição + grão único em cena e pessoa (esconde emenda de recorte)
    out = bg * (1 - a_f[..., None]) + sub * a_f[..., None]
    out += np.random.RandomState(int(seed) % 100000).normal(0, 2.4, (_H, _W, 1)).astype(np.float32)
    img = Image.fromarray(np.clip(out, 0, 255).astype(np.uint8))
    img = _grade_estilo(img, "cinematic" if estilo == "cinematic" else "showcase")
    return img, corpo, _caixa_cabeca(a_f)


# ── v58: correções da integração (rosto e mãos intocados, borda limpa, sem halo) ─────
def _limpar_borda_v58(rgba):
    """Recorte mais limpo: encolhe ~2px, repinta a borda com a cor de dentro e suaviza o alpha."""
    import cv2
    a = np.asarray(rgba.split()[3]).astype(np.float32) / 255.0
    rgb = np.asarray(rgba.convert("RGB")).astype(np.float32)
    a = np.clip((a - 0.18) / 0.64, 0, 1)
    nucleo = cv2.erode(a, cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (9, 9)))
    num = cv2.GaussianBlur(rgb * nucleo[..., None], (0, 0), 5)
    den = cv2.GaussianBlur(nucleo, (0, 0), 5)[..., None]
    sangra = num / np.maximum(den, 1e-3)
    w = np.clip(1.0 - nucleo, 0, 1)[..., None] * (den > 0.04)
    rgb = rgb * (1 - w) + sangra * w
    a = cv2.erode(a, cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (5, 5)))
    a = cv2.GaussianBlur(a, (0, 0), 0.9)
    return rgb, a


def _zona_rosto_v58(a_f):
    """(x0, y0, x1, y1) de cabeça + pescoço: do topo da cabeça até o início dos ombros."""
    m = a_f > 0.04
    tem = m.any(axis=1)
    linhas = np.where(tem)[0]
    if len(linhas) == 0:
        return None
    esq = np.argmax(m, axis=1)
    dire = _W - 1 - np.argmax(m[:, ::-1], axis=1)
    larg = np.where(tem, dire - esq, 0)
    y_topo = int(linhas[0])
    jan = larg[y_topo: y_topo + max(10, int(_H * 0.05))]
    ref = float(np.median(jan[jan > 0])) if np.any(jan > 0) else 0.0
    y_ombro = y_topo + int(_H * 0.16)
    if ref > 0:
        for r in range(y_topo, min(_H, y_topo + int(_H * 0.40))):
            if larg[r] > ref * 1.5:
                y_ombro = r
                break
    y1 = max(y_topo + 20, y_ombro - 12)
    x0 = int(esq[y_topo:y1][tem[y_topo:y1]].min()) - 12
    x1 = int(dire[y_topo:y1][tem[y_topo:y1]].max()) + 12
    return max(0, x0), max(0, y_topo - 12), min(_W, x1), y1


# ══════════════════════════════════════════════════════════════════════════════
# v65 — COR DA ROUPA: verifica e, se preciso, RECOLORE (não "pinta")
#  • mede a cor dominante da camisa (k-means em Lab, só roupa; rosto/mãos/pele ficam de fora)
#  • decide: mantém se já combina com a paleta e contrasta com a cena; senão troca para uma
#    cor da paleta (petróleo, marinho, sálvia, branco) escolhida pelo contraste com o cenário
#  • a troca preserva a luminosidade/textura do tecido (dobras, costuras), só muda o tom
#  • o ajuste antigo (mistura de cor da cena + dessaturação) foi removido: era ele que "pintava"
# ══════════════════════════════════════════════════════════════════════════════
_PALETA_ROUPA = {
    "petroleo": (27, 121, 125),
    "marinho": (2, 64, 89),
    "salvia": (119, 153, 147),
    "branco": (244, 246, 248),
}
_PESO_ROUPA = {"petroleo": 1.0, "marinho": 0.95, "salvia": 0.8, "branco": 0.7}


def _lab_de_rgb(rgb):
    import cv2
    return cv2.cvtColor(np.array([[rgb]], np.float32) / 255.0, cv2.COLOR_RGB2LAB)[0, 0].astype(np.float32)


def _recolorir_roupa(sub, a_f, protege, amb, seed, corpo):
    """sub: (H,W,3) float 0-255 do corpo no canvas; a_f: alpha; protege: (H,W) rosto/pele.
    Retorna sub com a camisa mantida ou recolorida. Qualquer falha devolve sub intacto."""
    import cv2
    try:
        ys, xs = np.where(a_f > 0.5)
        if len(ys) < 3000:
            return sub
        y_a, y_b, x_a, x_b = int(ys.min()), int(ys.max()) + 1, int(xs.min()), int(xs.max()) + 1
        crop = np.clip(sub[y_a:y_b, x_a:x_b], 0, 255).astype(np.float32) / 255.0
        a_c = a_f[y_a:y_b, x_a:x_b]
        p_c = protege[y_a:y_b, x_a:x_b]
        lab = cv2.cvtColor(crop, cv2.COLOR_RGB2LAB)
        h = y_b - y_a
        livre = (a_c > 0.5) & (p_c < 0.3)

        # faixa onde está a camisa (abaixo da cabeça, acima do quadril estimado)
        topo, base = int(h * (0.18 if corpo else 0.10)), int(h * (0.52 if corpo else 0.88))
        faixa = livre.copy()
        faixa[:topo] = False
        faixa[base:] = False
        idx = np.argwhere(faixa)
        if len(idx) < 1500:
            return sub
        if len(idx) > 6000:
            idx = idx[np.random.RandomState(1).choice(len(idx), 6000, replace=False)]
        amostra = lab[idx[:, 0], idx[:, 1]].astype(np.float32)
        crit = (cv2.TERM_CRITERIA_EPS + cv2.TERM_CRITERIA_MAX_ITER, 20, 1.0)
        _, rot, cent = cv2.kmeans(amostra, 3, None, crit, 3, cv2.KMEANS_PP_CENTERS)
        dom = cent[int(np.argmax(np.bincount(rot.ravel(), minlength=3)))]

        amb_lab = _lab_de_rgb(tuple(float(v) for v in np.clip(amb, 0, 255)))
        pal_lab = {k: _lab_de_rgb(v) for k, v in _PALETA_ROUPA.items()}
        de = lambda p, q: float(np.linalg.norm(p - q))
        croma = float(np.hypot(dom[1], dom[2]))
        de_pal = min(de(dom, v) for v in pal_lab.values())
        contraste = abs(float(dom[0]) - float(amb_lab[0]))

        # 1) a cor atual já serve? (parece da paleta, ou neutra, e se destaca do cenário)
        combina = de_pal <= 24 or (croma <= 9 and 25 < dom[0] < 92)
        if combina and contraste >= 18:
            return sub

        # 2) escolhe a cor-alvo da paleta pelo contraste/separação com o cenário
        rnd = np.random.RandomState(int(seed) % 100000)
        melhor = None
        for nome, plab in pal_lab.items():
            c_l = min(abs(float(plab[0]) - float(amb_lab[0])), 50.0) / 50.0
            sep = min(de(plab, amb_lab), 60.0) / 60.0
            sc = _PESO_ROUPA[nome] * (0.6 * c_l + 0.4 * sep) + 0.08 * rnd.rand()
            if melhor is None or sc > melhor[0]:
                melhor = (sc, nome, plab)
        _, nome_alvo, alvo = melhor

        # 3) máscara da camisa: mesmo matiz (a,b) da cor dominante, tolerando sombra/luz (L); sem pele/rosto
        dab = np.hypot(lab[..., 1] - dom[1], lab[..., 2] - dom[2])
        dl = np.abs(lab[..., 0] - dom[0])
        # pele por Lab (a 5..28, b 8..34): camisa vermelha/rosa/laranja NAO e pele
        pele_cor = ((lab[..., 1] >= 5) & (lab[..., 1] <= 28) & (lab[..., 2] >= 8) & (lab[..., 2] <= 34)
                    & (lab[..., 0] > 25) & (lab[..., 0] < 92)).astype(np.uint8)
        pele_cor = cv2.dilate(pele_cor, np.ones((5, 5), np.uint8)) > 0
        # mesmo matiz com mais croma (sombras da própria camisa) também entra, se a camisa tem cor própria
        ang = np.arctan2(lab[..., 2], lab[..., 1])
        dang = np.abs(np.angle(np.exp(1j * (ang - float(np.arctan2(dom[2], dom[1]))))))
        mesmo_matiz = (np.hypot(lab[..., 1], lab[..., 2]) > 4) & (dang < 0.45) if croma >= 9 else False
        mascara = livre & (dl < 45) & (~pele_cor) & ((dab < 24) | mesmo_matiz)
        # começa nos ombros (largura do corpo salta em relação à da cabeça): nunca recolore rosto/pescoço
        larg = (a_c > 0.5).sum(axis=1).astype(np.float32)
        ref = float(np.median(larg[: max(8, int(h * 0.05))][larg[: max(8, int(h * 0.05))] > 0])) \
            if (larg[: max(8, int(h * 0.05))] > 0).any() else 0.0
        ombro = None
        if ref > 0:
            for r in range(int(h * 0.03), int(h * 0.55)):
                if larg[r] > ref * 1.45:
                    ombro = r
                    break
        mascara[: int(h * 0.02)] = False  # v66: sem corte nos ombros/quadril; a protecao de rosto/pele ja exclui o resto
        limite = int(h * (0.75 if corpo else 0.97))
        mascara[limite:] = False
        mascara = cv2.morphologyEx(mascara.astype(np.uint8), cv2.MORPH_OPEN, np.ones((3, 3), np.uint8))
        mascara = cv2.morphologyEx(mascara, cv2.MORPH_CLOSE, np.ones((5, 5), np.uint8))
        # v69: areas claras da pele (rosto/maos) pareciam camisa clara e eram recoloridas (manchas azuladas).
        # So e camisa o que NAO esta cercado de pele e pertence a um bloco continuo relevante.
        dens_pele = cv2.blur(pele_cor.astype(np.float32), (41, 41))
        mascara = np.where(dens_pele > 0.18, 0, mascara).astype(np.uint8)
        n_cc, rot_cc, st_cc, _ = cv2.connectedComponentsWithStats(mascara)
        if n_cc > 1:
            area_max = int(st_cc[1:, cv2.CC_STAT_AREA].max())
            manter = np.zeros(n_cc, dtype=bool)
            for k in range(1, n_cc):
                if int(st_cc[k, cv2.CC_STAT_AREA]) >= 0.06 * area_max:
                    manter[k] = True
            mascara = manter[rot_cc].astype(np.uint8)
        corpo_px = max(int((a_c > 0.5).sum()), 1)
        frac = float(mascara.sum()) / corpo_px
        if frac < 0.04 or frac > 0.75:  # máscara implausível: não mexe
            return sub
        m = cv2.GaussianBlur(mascara.astype(np.float32), (0, 0), 1.2) * (a_c > 0.3)

        # 4) recolore preservando a luz/textura do tecido: L acompanha, a/b vão para o alvo
        novo = lab.copy()
        novo[..., 0] = np.clip(lab[..., 0] + (float(alvo[0]) - float(dom[0])) * 0.65, 4, 98)
        novo[..., 1] = float(alvo[1]) + (lab[..., 1] - float(dom[1])) * 0.35
        novo[..., 2] = float(alvo[2]) + (lab[..., 2] - float(dom[2])) * 0.35
        rec = np.clip(cv2.cvtColor(novo, cv2.COLOR_LAB2RGB), 0, 1) * 255.0
        out = sub.copy()
        out[y_a:y_b, x_a:x_b] = sub[y_a:y_b, x_a:x_b] * (1 - m[..., None]) + rec * m[..., None]
        print(f"[roupa] cor atual Lab=({dom[0]:.0f},{dom[1]:.0f},{dom[2]:.0f}) -> {nome_alvo}")
        return out
    except Exception as e:
        print(f"[roupa] recoloracao ignorada: {e}")
        return sub


def _integrar_v58(fundo, recorte, estilo, seed):
    """Retorna (imagem RGB, corpo_inteiro, caixa_da_cabeca, x_esquerdo_do_corpo)."""
    import cv2
    rgb_r, a_r = _limpar_borda_v58(recorte)
    ys, xs = np.where(a_r > 0.04)
    if len(ys) == 0:
        raise ErroEstilo("O recorte do Ronilson veio vazio.")
    rgb_r = rgb_r[ys.min():ys.max() + 1, xs.min():xs.max() + 1]
    a_r = a_r[ys.min():ys.max() + 1, xs.min():xs.max() + 1]
    ph, pw = a_r.shape
    prop = ph / pw

    corpo = prop >= 2.2
    if corpo:
        alt = int(_H * 0.86)
    else:
        larg_alvo = int(_W * (0.50 if prop >= 1.35 else 0.54))
        alt = min(int(larg_alvo * prop), _H)
    nw = max(1, int(alt / prop))
    rgb_s = cv2.resize(rgb_r, (nw, alt), interpolation=cv2.INTER_AREA)
    a_s = cv2.resize(a_r, (nw, alt), interpolation=cv2.INTER_AREA)
    x0 = max(int(_W * 0.46), _W - nw - int(_W * 0.02))
    y0 = int(_H * 0.975) - alt if corpo else _H - alt
    # v68: a sombra de estudio sob os sapatos (alpha parcial) aparece como "mancha": corta abaixo do ultimo pixel solido
    if corpo:
        try:
            _lin = np.where((a_s > 0.85).sum(axis=1) > 2)[0]
            if len(_lin):
                a_s[min(alt, int(_lin.max()) + 4):, :] = 0.0
        except Exception as e:
            print(f"[ronilson] limpar sombra do estudio ignorado: {e}")
    # v68: foto cortada na lateral (corte reto): a lateral reta encosta na borda do card e o titulo vai para o outro lado
    lado_x = "dir"
    try:
        _c_esq, _c_dir = _corte_reto(a_s, "esq"), _corte_reto(a_s, "dir")
        _n_r = min(90, nw // 3)
        _ramp = np.ones(nw, np.float32)
        if _c_esq and not _c_dir:
            x0, lado_x = -2, "esq"
        elif _c_dir and not _c_esq:
            x0 = _W - nw + 2
        elif _c_esq and _c_dir:  # cortada nos dois lados: dissolve as duas bordas
            _ramp[:_n_r] = np.linspace(0, 1, _n_r, dtype=np.float32) ** 1.5
            _ramp[nw - _n_r:] = np.linspace(1, 0, _n_r, dtype=np.float32) ** 1.5
        a_s = a_s * _ramp[None, :]
    except Exception as e:
        print(f"[ronilson] tratar corte reto ignorado: {e}")

    sub = np.zeros((_H, _W, 3), np.float32)
    a_f = np.zeros((_H, _W), np.float32)
    sx0, sy0 = max(0, -x0), max(0, -y0)
    dx0, dy0 = max(0, x0), max(0, y0)
    cw, ch = min(nw - sx0, _W - dx0), min(alt - sy0, _H - dy0)
    sub[dy0:dy0 + ch, dx0:dx0 + cw] = rgb_s[sy0:sy0 + ch, sx0:sx0 + cw]
    a_f[dy0:dy0 + ch, dx0:dx0 + cw] = a_s[sy0:sy0 + ch, sx0:sx0 + cw]

    fundo = fundo.convert("RGB").resize((_W, _H), Image.Resampling.LANCZOS)
    fundo = fundo.filter(ImageFilter.GaussianBlur(_BLUR_CENARIO.get(estilo, 2.0)))
    bg = np.asarray(fundo).astype(np.float32)

    lum = bg.mean(axis=2)
    luz_x = -1.0 if lum[:, : _W // 2].mean() >= lum[:, _W // 2:].mean() * 0.95 else 1.0
    solido = (a_f > 0.5).astype(np.uint8)
    anel = cv2.dilate(solido, np.ones((41, 41), np.uint8)) - solido
    amb = bg[anel > 0].mean(axis=0) if anel.any() else bg.reshape(-1, 3).mean(axis=0)

    # proteção: rosto, pescoço e mãos (pele) NÃO recebem nenhum ajuste
    orig = sub.copy()
    fm = np.zeros((_H, _W), np.float32)
    zr = _zona_rosto_v58(a_f)
    if zr:
        fm[zr[1]:zr[3], zr[0]:zr[2]] = 1.0
        fm = cv2.GaussianBlur(fm, (0, 0), 5)
    ycc = cv2.cvtColor(np.clip(sub, 0, 255).astype(np.uint8), cv2.COLOR_RGB2YCrCb).astype(np.int32)
    Yc, Cr, Cb = ycc[..., 0], ycc[..., 1], ycc[..., 2]
    # v66: pele por Lab (a 5..28, b 8..34): camisa vermelha/rosa/laranja NAO e pele
    _ys, _xs = np.where(a_f > 0.5)
    pele = np.zeros(a_f.shape, np.uint8)
    if len(_ys):
        _y0, _y1, _x0, _x1 = _ys.min(), _ys.max() + 1, _xs.min(), _xs.max() + 1
        _lab = cv2.cvtColor(np.clip(sub[_y0:_y1, _x0:_x1], 0, 255).astype(np.float32) / 255.0, cv2.COLOR_RGB2LAB)
        _sk = ((_lab[..., 1] >= 5) & (_lab[..., 1] <= 28) & (_lab[..., 2] >= 8) & (_lab[..., 2] <= 34)
               & (_lab[..., 0] > 25) & (_lab[..., 0] < 92) & (a_f[_y0:_y1, _x0:_x1] > 0.5))
        pele[_y0:_y1, _x0:_x1] = _sk.astype(np.uint8)
        del _lab, _sk
    pele = cv2.morphologyEx(pele, cv2.MORPH_OPEN, np.ones((3, 3), np.uint8))
    pele = cv2.morphologyEx(pele, cv2.MORPH_CLOSE, np.ones((9, 9), np.uint8))
    _n_c, _lab, _st, _ = cv2.connectedComponentsWithStats(pele)
    _area_corpo = max(int((a_f > 0.5).sum()), 1)
    for _k in range(1, _n_c):
        if _st[_k, cv2.CC_STAT_AREA] > 0.06 * _area_corpo:
            _comp = _lab == _k
            if not (fm[_comp] > 0.3).any():  # mancha grande fora do rosto = roupa; rosto+pescoco ficam
                pele[_comp] = 0
    del _lab
    pele = cv2.GaussianBlur(pele.astype(np.float32), (0, 0), 2)
    protege = np.clip(np.maximum(fm, pele), 0, 1) * np.clip(a_f * 1.5, 0, 1)
    protege = protege[..., None]

    # 1) roupa/corpo: a cor so muda por recoloracao consciente (v65); depois so a exposicao acompanha a cena
    sub = _recolorir_roupa(sub, a_f, protege[..., 0], amb, seed, corpo)
    media_l = float(sub[solido > 0].mean())
    expo = float(np.clip((amb.mean() + 55) / (media_l + 55), 0.82, 1.06))
    sub = sub * (expo ** 0.5)

    # 2) luz direcional suave
    X = np.linspace(0, 1, _W, dtype=np.float32)[None, :]
    t = np.clip((X - x0 / _W) / max(nw / _W, 1e-3), 0, 1)
    t = t if luz_x > 0 else 1 - t
    sub *= (1.04 - 0.12 * t)[..., None]
    sub *= (1.0 - 0.05 * np.linspace(0, 1, _H, dtype=np.float32))[:, None, None]

    # 3) light wrap e contorno de luz discretos (sem halo)
    bg_suave = cv2.GaussianBlur(bg, (0, 0), 20)
    nucleo = cv2.GaussianBlur(cv2.erode(a_f, np.ones((9, 9), np.uint8)), (0, 0), 2)
    borda = np.clip(a_f - nucleo, 0, 1)[..., None]
    sub = sub * (1 - 0.20 * borda) + bg_suave * 0.20 * borda
    lado = np.clip(1 - t * 2.0, 0, 1)[..., None]
    rim = np.array([255, 205, 130], np.float32) * 0.5 + amb * 0.6
    sub = sub + 0.12 * borda * lado * rim * (1 - sub / 255.0)

    # rosto/mãos: pixels originais, sem nenhum ajuste
    sub = sub * (1 - protege) + orig * protege

    # 4) sombras: projetada curta e suave + contato no chão (sem aura em volta)
    sil = cv2.GaussianBlur(a_f, (0, 0), 14)
    desloc = np.float32([[1, 0, -luz_x * 42], [0, 1, 12]])
    sombra = cv2.warpAffine(sil, desloc, (_W, _H))
    sombra = sombra * (1 - np.clip(cv2.GaussianBlur(a_f, (0, 0), 2), 0, 1))
    sombra = sombra * (0.0 if corpo else 0.5)  # v68: sem sombra projetada "fantasma" no fundo (corpo inteiro: so contato)
    if corpo:
        chao = np.zeros((_H, _W), np.float32)
        _ys_s = np.where((a_f > 0.35).any(axis=1))[0]
        base_y = int(_ys_s.max()) if len(_ys_s) else int(y0 + alt - 4)
        banda_h = max(12, int(alt * 0.07))
        yb0 = max(0, base_y - banda_h)
        faixa = (a_f[yb0:base_y + 1] > 0.35).astype(np.uint8)
        n_f, _, st_f, cen_f = cv2.connectedComponentsWithStats(faixa)
        pes_l = [(int(cen_f[k][0]), yb0 + st_f[k, cv2.CC_STAT_TOP] + st_f[k, cv2.CC_STAT_HEIGHT],
                  int(st_f[k, cv2.CC_STAT_WIDTH])) for k in range(1, n_f) if st_f[k, cv2.CC_STAT_AREA] >= 40]
        if pes_l:  # uma sombra de contato por pe; pe levantado ganha sombra no chao logo abaixo
            y_max = max(p[1] for p in pes_l)
            for xk, ylow, wk in pes_l:
                dif = y_max - ylow
                yy_s = ylow - 2 if dif <= 10 else ylow + int(0.6 * dif) + 3
                forca = 1.0 if dif <= 10 else 0.7
                cv2.ellipse(chao, (xk, yy_s), (int(max(26, wk * 0.85)), int(_H * 0.011) + 5), 0, 0, 360, forca, -1)
        else:
            cx = x0 + nw // 2
            cv2.ellipse(chao, (cx, base_y), (int(nw * 0.4), int(_H * 0.012) + 5), 0, 0, 360, 1.0, -1)
        chao = cv2.GaussianBlur(chao, (0, 0), 10)
        sombra = np.clip(sombra + 1.5 * chao, 0, 1)
        degrade = np.clip((np.arange(_H, dtype=np.float32) - (base_y - 30)) / 160.0, 0, 1)
        bg = bg * (1 - 0.18 * degrade)[:, None, None]
    s = (0.32 * sombra)[..., None]
    bg = bg * (1 - s) + (amb * 0.20) * s

    # 5) composição; grão e correção de cor da cena NÃO entram no rosto/mãos
    out = bg * (1 - a_f[..., None]) + sub * a_f[..., None]
    sem_grao = np.clip(out, 0, 255).astype(np.uint8)
    grao = np.random.RandomState(int(seed) % 100000).normal(0, 2.4, (_H, _W, 1)).astype(np.float32)
    graduada = _grade_estilo(Image.fromarray(np.clip(out + grao, 0, 255).astype(np.uint8)),
                             "cinematic" if estilo == "cinematic" else "showcase")
    P = (protege[..., 0] * a_f)[..., None]
    final = np.asarray(graduada).astype(np.float32) * (1 - P) + sem_grao.astype(np.float32) * P
    img = Image.fromarray(np.clip(final, 0, 255).astype(np.uint8))

    # onde o corpo começa (para o título saber a largura livre)
    r0, r1 = int(_H * 0.35), int(_H * 0.92)
    cols = np.where((a_f[r0:r1] > 0.3).any(axis=0))[0]
    x_esq = int(cols.min()) if len(cols) else x0
    x_dir = int(cols.max()) if len(cols) else x0 + nw
    return img, corpo, _caixa_cabeca(a_f), x_esq, lado_x, x_dir


# ══════════════════════════════════════════════════════════════════════════════
# v59 — INTELIGÊNCIA DE CENÁRIO + integração do Ronilson
#  • valida o cenário: sem pessoas (Haar + Gemini visão), sem objetos gigantes/poluição
#  • posição escolhida pela região menos poluída; chão detectado; luz pelo centro de brilho
#  • recorte com corte reto (foto cortada): ancora a lateral na borda do card e o título
#    passa para o lado oposto
#  • cada pé recebe a própria sombra de contato (pé levantado não "flutua")
#  • borda do recorte: sem franja clara, rosto/mãos protegidos, camisa rosa não vira "pele"
# ══════════════════════════════════════════════════════════════════════════════
_EXTRA_ESCALA_CENARIO = (
    " Keep every object small, distant and softly out of focus; absolutely no oversized foreground "
    "leaves, plants or foliage, no large dark shapes; the wall and the floor must be clearly visible "
    "and calm."
)


def _prompt_cenario_v59(estilo, tema, seed, tentativa=0):
    p = _prompt_cenario_ronilson(estilo, tema, seed) + _EXTRA_ESCALA_CENARIO
    if tentativa > 0:
        p += (" IMPORTANT: the previous attempt contained a person or oversized elements. Make a simple, "
              "EMPTY interior/architectural scene only. No human figure of any kind, not even a silhouette, "
              "a reflection, a statue or a portrait.")
    return p


def _tem_rosto_haar(img):
    """True se achar rosto (frontal ou de perfil) no cenário."""
    try:
        import cv2
        g = cv2.equalizeHist(np.asarray(img.convert("L").resize((540, 675))))
        for nome, viz in (("haarcascade_frontalface_default.xml", 6), ("haarcascade_frontalface_alt2.xml", 5),
                          ("haarcascade_profileface.xml", 5)):
            c = cv2.CascadeClassifier(cv2.data.haarcascades + nome)
            if c.empty():
                continue
            for im in ((g, cv2.flip(g, 1)) if "profile" in nome else (g,)):
                if len(c.detectMultiScale(im, scaleFactor=1.08, minNeighbors=viz, minSize=(56, 56))):
                    return True
    except Exception as e:
        print(f"[cenario] Haar falhou: {e}")
    return False


def _gemini_tem_pessoa(img):
    """Visão do Gemini: True/False, ou None se não deu para consultar."""
    M = _m()
    chave = getattr(M, "GEMINI_API_KEY", None)
    if not chave:
        return None
    try:
        buf = io.BytesIO()
        img.convert("RGB").resize((384, 480)).save(buf, "JPEG", quality=80)
        payload = {
            "contents": [{"parts": [
                {"text": "Does this image contain any person, face, human body part, hand or human "
                         "silhouette (even blurred, dark, partial, in the background or as a portrait)? "
                         "Answer with exactly one word: SIM or NAO."},
                {"inline_data": {"mime_type": "image/jpeg", "data": base64.b64encode(buf.getvalue()).decode()}},
            ]}],
            "generationConfig": {"temperature": 0},
        }
    except Exception as e:
        print(f"[cenario] visao Gemini (preparo) falhou: {e}")
        return None
    for modelo in ("gemini-2.5-flash", "gemini-3.5-flash"):
        try:
            r = requests.post(f"https://generativelanguage.googleapis.com/v1beta/models/{modelo}:generateContent"
                              f"?key={chave}", json=payload, timeout=20)
            if r.status_code >= 400:
                continue
            partes = r.json()["candidates"][0]["content"]["parts"]
            txt = "".join(p.get("text", "") for p in partes if not p.get("thought")).strip().upper()
            if txt.startswith("SIM"):
                return True
            if txt.startswith("NAO") or txt.startswith("NÃO"):
                return False
        except Exception as e:
            print(f"[cenario] visao Gemini {modelo}: {e}")
    return None


def _pequeno_cinza(img):
    import cv2
    g = np.asarray(img.convert("L").resize((270, 340))).astype(np.float32)
    return cv2.GaussianBlur(g, (0, 0), 3)


def _complexidade_cenario(img):
    """Desvio de luminância na região onde o corpo vai ficar: alto = poluído / objeto grande."""
    g = _pequeno_cinza(img)
    return float(g[int(340 * 0.10):, int(270 * 0.44):].std())


def _cenario_ronilson_v59(estilo, tema, seed):
    """Gera o cenário e VALIDA. Até 2 tentativas; se vier pessoa, cai no gradiente da paleta."""
    M = _m()
    t0 = time.time()
    melhor = None
    for tentativa in range(2):
        img, motivo = _gerar_imagem_ia(_prompt_cenario_v59(estilo, tema, seed + tentativa * 17, tentativa))
        if img is None:
            print(f"[cenario] IA falhou ({motivo})")
            break
        pessoa = _tem_rosto_haar(img)
        if not pessoa:
            pessoa = _gemini_tem_pessoa(img) is True
        score = _complexidade_cenario(img)
        print(f"[cenario] tentativa {tentativa + 1}: pessoa={pessoa} poluicao={score:.1f}")
        if not pessoa and score <= 55:
            return img, None
        if melhor is None or (pessoa, score) < (melhor[0], melhor[1]):
            melhor = (pessoa, score, img)
        if time.time() - t0 > 45:
            break
    if melhor is not None and not melhor[0]:
        return melhor[2], None
    aviso = ("O cenario gerado tinha pessoa ou nao pôde ser gerado; usei o gradiente da paleta."
             if melhor is not None else "O cenario por IA falhou; usei o gradiente da paleta.")
    return M._gerar_fundo_gradiente(M.MARINHO, M.PETROLEO, seed), aviso


def _linha_do_chao(bg):
    """y da transição parede/chão (maior mudança de brilho entre 55% e 95% da altura), ou None."""
    import cv2
    perfil = cv2.GaussianBlur(bg.mean(axis=2).mean(axis=1).astype(np.float32).reshape(-1, 1), (0, 0), 12).ravel()
    d = np.abs(np.diff(perfil))
    a, b = int(_H * 0.55), int(_H * 0.95)
    k = int(np.argmax(d[a:b])) + a
    return k if d[k] > 0.35 else None


def _limpar_borda_v59(rgba):
    """Borda sem franja clara: corta alpha fraco, encolhe ~3px, repinta a borda com a cor de dentro
    e trava qualquer pixel de borda mais claro que o interior vizinho."""
    import cv2
    a = np.asarray(rgba.split()[3]).astype(np.float32) / 255.0
    rgb = np.asarray(rgba.convert("RGB")).astype(np.float32)
    a = np.clip((a - 0.30) / 0.55, 0, 1)
    nucleo = cv2.erode(a, cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (11, 11)))
    num = cv2.GaussianBlur(rgb * nucleo[..., None], (0, 0), 6)
    den = cv2.GaussianBlur(nucleo, (0, 0), 6)[..., None]
    sangra = num / np.maximum(den, 1e-3)
    banda = (np.clip(1.0 - nucleo, 0, 1)[..., None]) * (den > 0.03)
    rgb = rgb * (1 - banda) + sangra * banda
    rgb = np.where(banda > 0.02, np.minimum(rgb, sangra * 1.06 + 4), rgb)
    a = cv2.erode(a, cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (7, 7)))
    a = cv2.GaussianBlur(a, (0, 0), 1.0)
    return rgb, a


def _corte_reto(a, lado):
    """True se a lateral do recorte tem um corte reto longo (foto cortada). lado: 'esq' ou 'dir'.
    Reto = borda praticamente constante (desvio <= 0,7px) por pelo menos 18% da altura."""
    m = a > 0.5
    tem = m.any(axis=1)
    if not tem.any():
        return False
    ph = a.shape[0]
    borda = np.argmax(m, axis=1) if lado == "esq" else (m.shape[1] - 1 - np.argmax(m[:, ::-1], axis=1))
    ref = borda[tem].min() if lado == "esq" else borda[tem].max()
    ok = tem & (np.abs(borda - ref) <= 3)
    runs, ini, falhas = [], None, 0
    for i, v in enumerate(ok):
        if v:
            if ini is None:
                ini = i
            falhas = 0
        elif ini is not None:
            falhas += 1
            if falhas > 4:
                runs.append((ini, i - falhas))
                ini, falhas = None, 0
    if ini is not None:
        runs.append((ini, len(ok) - 1 - falhas))
    for r0, r1 in runs:
        if (r1 - r0 + 1) >= 0.18 * ph and float(borda[r0:r1 + 1].std()) <= 0.7:
            return True
    return False


def _integrar_v59(fundo, recorte, estilo, seed):
    """Retorna (imagem RGB, corpo_inteiro, caixa_da_cabeca, info) com info = {lado, x_esq, x_dir}."""
    import cv2
    rgb_r, a_r = _limpar_borda_v59(recorte)
    ys, xs = np.where(a_r > 0.04)
    if len(ys) == 0:
        raise ErroEstilo("O recorte do Ronilson veio vazio.")
    rgb_r = rgb_r[ys.min():ys.max() + 1, xs.min():xs.max() + 1]
    a_r = a_r[ys.min():ys.max() + 1, xs.min():xs.max() + 1]
    ph, pw = a_r.shape
    prop = ph / pw
    corte_esq, corte_dir = _corte_reto(a_r, "esq"), _corte_reto(a_r, "dir")

    fundo = fundo.convert("RGB").resize((_W, _H), Image.Resampling.LANCZOS)
    fundo = fundo.filter(ImageFilter.GaussianBlur(_BLUR_CENARIO.get(estilo, 2.0)))
    bg = np.asarray(fundo).astype(np.float32)
    y_chao = _linha_do_chao(bg)

    corpo = prop >= 2.2
    feet_y = int(np.clip((y_chao + 0.05 * _H) if y_chao else 0.975 * _H, 0.90 * _H, 0.975 * _H))
    if corpo:
        alt = min(int(_H * 0.86), feet_y - int(_H * 0.07))
    else:
        larg_alvo = int(_W * (0.50 if prop >= 1.35 else 0.54))
        alt = min(int(larg_alvo * prop), _H)
    nw = max(1, int(alt / prop))
    rgb_s = cv2.resize(rgb_r, (nw, alt), interpolation=cv2.INTER_AREA)
    a_s = cv2.resize(a_r, (nw, alt), interpolation=cv2.INTER_AREA)
    y0 = feet_y - alt if corpo else _H - alt

    # lado: foto cortada na lateral -> a lateral reta fica ENCOSTADA na borda do card
    if corte_esq and not corte_dir:
        lado, x0 = "esq", -2
    elif corte_dir and not corte_esq:
        lado, x0 = "dir", _W - nw + 2
    elif corte_esq and corte_dir:
        lado, x0 = "dir", _W - nw + 2
    else:
        lado = "dir"
        x_max = _W - nw - int(_W * 0.02)
        x_min = min(int(_W * 0.46), x_max)
        cands = sorted(set(int(v) for v in np.linspace(x_min, x_max, 4)))
        g = _pequeno_cinza(fundo)
        melhor_c = None
        for cx in cands:
            gx0, gx1 = int(cx / _W * 270), int(min(_W, cx + nw) / _W * 270)
            gy0, gy1 = int(max(0, y0) / _H * 340), 340
            reg = g[gy0:gy1, gx0:max(gx0 + 2, gx1)]
            sc = float(reg.std()) - 0.004 * (cx - x_min)  # leve preferência pela direita
            if melhor_c is None or sc < melhor_c[0]:
                melhor_c = (sc, cx)
        x0 = melhor_c[1]

    # corte reto que NÃO ficou encostado na borda do card: dissolve a lateral (sem "quina" visível)
    rampa = np.ones(nw, np.float32)
    n_r = min(90, nw // 3)
    if lado == "dir" and corte_esq:
        rampa[:n_r] = np.linspace(0, 1, n_r, dtype=np.float32) ** 1.5
    elif lado == "esq" and corte_dir:
        rampa[nw - n_r:] = np.linspace(1, 0, n_r, dtype=np.float32) ** 1.5
    a_s = a_s * rampa[None, :]

    sub = np.zeros((_H, _W, 3), np.float32)
    a_f = np.zeros((_H, _W), np.float32)
    sx0, sy0 = max(0, -x0), max(0, -y0)
    dx0, dy0 = max(0, x0), max(0, y0)
    cw, ch = min(nw - sx0, _W - dx0), min(alt - sy0, _H - dy0)
    sub[dy0:dy0 + ch, dx0:dx0 + cw] = rgb_s[sy0:sy0 + ch, sx0:sx0 + cw]
    a_f[dy0:dy0 + ch, dx0:dx0 + cw] = a_s[sy0:sy0 + ch, sx0:sx0 + cw]

    # luz: centro de brilho do cenário em relação à pessoa
    ls = cv2.resize(bg.mean(axis=2), (54, 68), interpolation=cv2.INTER_AREA)
    pesos = np.clip(ls - np.percentile(ls, 40), 0, None) ** 2
    cx_luz = float((pesos * np.arange(54)[None, :]).sum() / max(pesos.sum(), 1e-3)) / 54 * _W
    luz_x = -1.0 if cx_luz < (x0 + nw / 2) else 1.0

    solido = (a_f > 0.5).astype(np.uint8)
    anel = cv2.dilate(solido, np.ones((41, 41), np.uint8)) - solido
    amb = bg[anel > 0].mean(axis=0) if anel.any() else bg.reshape(-1, 3).mean(axis=0)

    # proteção: rosto, pescoço e mãos NÃO recebem ajuste (borda externa de ~3px recebe tratamento)
    orig = sub.copy()
    fm = np.zeros((_H, _W), np.float32)
    zr = _zona_rosto_v58(a_f)
    if zr:
        zr = (zr[0], zr[1], zr[2], zr[1] + int((zr[3] - zr[1]) * 0.88))  # só a cabeça; o pescoço entra pela máscara de pele
        fm[zr[1]:zr[3], zr[0]:zr[2]] = 1.0
        fm = cv2.GaussianBlur(fm, (0, 0), 5)
    ycc = cv2.cvtColor(np.clip(sub, 0, 255).astype(np.uint8), cv2.COLOR_RGB2YCrCb).astype(np.int32)
    Yc, Cr, Cb = ycc[..., 0], ycc[..., 1], ycc[..., 2]
    R, G, B = sub[..., 0], sub[..., 1], sub[..., 2]
    pele = ((Cr >= 135) & (Cr <= 173) & (Cb >= 77) & (Cb <= 120) & (Yc > 45) & (Yc < 235)
            & (R > G) & (G >= B - 3) & ((R - B) > 18) & (a_f > 0.5)).astype(np.uint8)
    pele = cv2.morphologyEx(pele, cv2.MORPH_OPEN, np.ones((3, 3), np.uint8))
    pele = cv2.morphologyEx(pele, cv2.MORPH_CLOSE, np.ones((9, 9), np.uint8))
    n_c, lab, st, _ = cv2.connectedComponentsWithStats(pele)
    area_corpo = max(int(solido.sum()), 1)
    for k in range(1, n_c):
        if st[k, cv2.CC_STAT_AREA] > 0.06 * area_corpo:  # mancha grande = roupa, não pele
            pele[lab == k] = 0
    pele = cv2.GaussianBlur(pele.astype(np.float32), (0, 0), 2)
    nucleo_f = cv2.GaussianBlur(cv2.erode(a_f, np.ones((7, 7), np.uint8)), (0, 0), 1.5)
    protege = (np.clip(np.maximum(fm, pele), 0, 1) * np.clip(nucleo_f * 1.4, 0, 1))[..., None]

    # 1) roupa/corpo: cor e exposição da cena + nível de preto do ambiente
    media = sub[solido > 0].mean(axis=0)
    ganho = (amb / max(amb.mean(), 1)) / (media / max(media.mean(), 1))
    ganho = np.clip(1 + 0.42 * (ganho - 1), 0.78, 1.22)
    expo = float(np.clip((amb.mean() + 55) / (media.mean() + 55), 0.58, 1.08))
    sub = sub * ganho * (expo ** 0.85)
    cinza = sub.mean(axis=2, keepdims=True)
    sat = (sub.max(axis=2, keepdims=True) - sub.min(axis=2, keepdims=True)) / (sub.max(axis=2, keepdims=True) + 1.0)
    sub = sub * (1 - 0.22 * np.clip(sat - 0.22, 0, 1)) + cinza * (0.22 * np.clip(sat - 0.22, 0, 1))
    bg_suave = cv2.GaussianBlur(bg, (0, 0), 20)
    sub = sub * 0.94 + bg_suave * 0.06

    # 2) luz direcional suave
    X = np.linspace(0, 1, _W, dtype=np.float32)[None, :]
    t = np.clip((X - x0 / _W) / max(nw / _W, 1e-3), 0, 1)
    t = t if luz_x > 0 else 1 - t
    sub *= (1.04 - 0.12 * t)[..., None]
    sub *= (1.0 - 0.05 * np.linspace(0, 1, _H, dtype=np.float32))[:, None, None]

    # 3) borda: absorve a cor do cenário (mais forte nos 2px externos) + contorno de luz discreto
    n4 = cv2.GaussianBlur(cv2.erode(a_f, np.ones((9, 9), np.uint8)), (0, 0), 2)
    n2 = cv2.GaussianBlur(cv2.erode(a_f, np.ones((5, 5), np.uint8)), (0, 0), 1)
    b4 = np.clip(a_f - n4, 0, 1)[..., None]
    b2 = np.clip(a_f - n2, 0, 1)[..., None]
    s_e = np.clip(0.20 * b4 + 0.32 * b2, 0, 0.55)
    sub = sub * (1 - s_e) + bg_suave * s_e
    lado_luz = np.clip(1 - t * 2.0, 0, 1)[..., None]
    rim = np.array([255, 205, 130], np.float32) * 0.5 + amb * 0.6
    sub = sub + 0.12 * b4 * lado_luz * rim * (1 - sub / 255.0)

    sub = sub * (1 - protege) + orig * protege  # rosto/mãos: pixels originais

    # 4) sombras: projetada curta e suave + contato POR PÉ
    sil = cv2.GaussianBlur(a_f, (0, 0), 14)
    desloc = np.float32([[1, 0, -luz_x * 42], [0, 1, 12]])
    sombra = cv2.warpAffine(sil, desloc, (_W, _H))
    sombra = sombra * (1 - np.clip(cv2.GaussianBlur(a_f, (0, 0), 2), 0, 1))
    if corpo:
        chao = np.zeros((_H, _W), np.float32)
        banda_h = max(12, int(alt * 0.07))
        yb0 = max(0, y0 + alt - banda_h)
        faixa = (a_f[yb0:y0 + alt] > 0.35).astype(np.uint8)
        n_f, _, st_f, cen_f = cv2.connectedComponentsWithStats(faixa)
        pes = [(int(cen_f[k][0]), yb0 + st_f[k, cv2.CC_STAT_TOP] + st_f[k, cv2.CC_STAT_HEIGHT],
                int(st_f[k, cv2.CC_STAT_WIDTH])) for k in range(1, n_f) if st_f[k, cv2.CC_STAT_AREA] >= 40]
        if pes:
            y_max = max(p[1] for p in pes)
            for xk, ylow, wk in pes:
                dif = y_max - ylow
                yy_s = ylow - 2 if dif <= 10 else ylow + int(0.6 * dif) + 3  # pé levantado: sombra no chão abaixo
                forca = 1.0 if dif <= 10 else 0.65
                cv2.ellipse(chao, (xk, yy_s), (int(max(24, wk * 0.8)), int(_H * 0.011) + 4), 0, 0, 360, forca, -1)
        else:
            cv2.ellipse(chao, (x0 + nw // 2, y0 + alt - 4), (int(nw * 0.4), int(_H * 0.012) + 4), 0, 0, 360, 1.0, -1)
        chao = cv2.GaussianBlur(chao, (0, 0), 10)
        sombra = np.clip(sombra + 0.8 * chao, 0, 1)
        degrade = np.clip((np.arange(_H, dtype=np.float32) - (y0 + alt - 30)) / 160.0, 0, 1)
        bg = bg * (1 - 0.16 * degrade)[:, None, None]
    s = (0.32 * sombra)[..., None]
    bg = bg * (1 - s) + (amb * 0.20) * s

    # 5) composição; grão e correção de cor da cena NÃO entram no rosto/mãos
    out = bg * (1 - a_f[..., None]) + sub * a_f[..., None]
    sem_grao = np.clip(out, 0, 255).astype(np.uint8)
    grao = np.random.RandomState(int(seed) % 100000).normal(0, 2.4, (_H, _W, 1)).astype(np.float32)
    graduada = _grade_estilo(Image.fromarray(np.clip(out + grao, 0, 255).astype(np.uint8)),
                             "cinematic" if estilo == "cinematic" else "showcase")
    P = (protege[..., 0] * a_f)[..., None]
    final = np.asarray(graduada).astype(np.float32) * (1 - P) + sem_grao.astype(np.float32) * P
    img = Image.fromarray(np.clip(final, 0, 255).astype(np.uint8))

    r0, r1 = int(_H * 0.35), int(_H * 0.92)
    cols = np.where((a_f[r0:r1] > 0.3).any(axis=0))[0]
    info = {"lado": lado,
            "x_esq": int(cols.min()) if len(cols) else x0,
            "x_dir": int(cols.max()) if len(cols) else x0 + nw}
    return img, corpo, _caixa_cabeca(a_f), info


# ══════════════════════════════════════════════════════════════════════════════
# v60 — VERSÃO LEVE do "Com Ronilson" (corrige 503/429/502 do v59)
#  • memória: recorte reduzido ANTES da limpeza + trabalho só na região do corpo (ROI)
#  • Cloudinary Admin API: pasta lembrada, cache (inclusive "vazio") e limite de chamadas
#  • Gemini: no máx. 2 gerações e só se vier pessoa; visão com 1 modelo e timeout curto
# ══════════════════════════════════════════════════════════════════════════════
def _listar_recortes_ronilson_v60():
    """Lista recortes da pasta ronilson_sem_fundo com cache de 10 min (e 90s se vier vazio/erro)."""
    import cloudinary.api
    M = _m()
    c = _cache_recortes
    agora = time.time()
    if c["lista"] and agora - c["t"] < 600:
        return c["lista"]
    if c.get("neg") and agora - c["neg"] < 90:
        return c["lista"]

    def _ok(r):
        pid = r.get("public_id", "")
        return (M.CLOUDINARY_POSTS not in pid and M.CLOUDINARY_PREVIEW not in pid
                and (r.get("format") or "png").lower() in ("png", "webp", "avif", "tiff", "tif"))

    def _limitado(e):
        t = str(e).lower()
        return "rate limit" in t or "420" in t or "429" in t

    achados, chamadas = [], 0
    prefixos = ([c["prefixo"]] if c.get("prefixo") else []) + \
               [p for p in _PREFIXOS_SEM_FUNDO if p != c.get("prefixo")]
    for pref in prefixos:
        cursor = None
        for _ in range(3):
            kw = dict(type="upload", prefix=pref + "/", max_results=100)
            if cursor:
                kw["next_cursor"] = cursor
            chamadas += 1
            try:
                res = cloudinary.api.resources(**kw)
            except Exception as e:
                print(f"[ronilson] '{pref}': {e}")
                if _limitado(e):
                    c["neg"] = agora
                    return c["lista"]
                break
            achados += [r for r in res.get("resources", []) if _ok(r)]
            cursor = res.get("next_cursor")
            if not cursor:
                break
        if achados:
            c["prefixo"] = pref
            print(f"[ronilson] {len(achados)} recortes em '{pref}' ({chamadas} chamadas)")
            break
        if chamadas >= 8:
            break

    if not achados and chamadas < 8:  # varredura geral, curta
        cursor = None
        for _ in range(3):
            kw = dict(type="upload", max_results=500)
            if cursor:
                kw["next_cursor"] = cursor
            try:
                res = cloudinary.api.resources(**kw)
            except Exception as e:
                print(f"[ronilson] varredura geral: {e}")
                break
            achados += [r for r in res.get("resources", [])
                        if _ok(r) and "sem_fundo" in r.get("public_id", "").lower().replace(" ", "_")]
            cursor = res.get("next_cursor")
            if not cursor:
                break

    if achados:
        c.update(t=time.time(), lista=achados, neg=0.0)
    else:
        c["neg"] = agora
    return achados or c["lista"]


def _carregar_recorte_ronilson_v60():
    """Sorteia (baralho) um recorte e baixa já reduzido pelo Cloudinary (leve). Retorna (RGBA, public_id)."""
    M = _m()
    recursos = _listar_recortes_ronilson_v60()
    if not recursos:
        raise ErroEstilo("Nao encontrei imagens na pasta ronilson_sem_fundo do Cloudinary "
                         "(PNG/WebP com transparencia). Tente de novo em instantes.")
    r = M._proxima_foto_baralho("ronilson_sem_fundo", recursos)
    url, pid = r.get("secure_url"), r.get("public_id", "")
    resp = None
    if "/upload/" in (url or ""):
        try:  # versão reduzida (mantém o alpha); se a conta bloquear transformações, usa o original
            resp = requests.get(url.replace("/upload/", "/upload/c_limit,w_1400,h_1800/", 1), timeout=30)
            if resp.status_code >= 400:
                resp = None
        except Exception as e:
            print(f"[ronilson] versao reduzida falhou: {e}")
    if resp is None:
        resp = requests.get(url, timeout=30)
        resp.raise_for_status()
    img = Image.open(io.BytesIO(resp.content))
    if img.mode in ("RGBA", "LA") or (img.mode == "P" and "transparency" in img.info):
        img = img.convert("RGBA")
    else:
        raise ErroEstilo(f"A imagem {pid} nao tem transparencia (fundo removido).")
    lado = max(img.size)
    if lado > 1600:
        f = 1600 / lado
        img = img.resize((int(img.width * f), int(img.height * f)), Image.Resampling.LANCZOS)
    print(f"[ronilson] recorte: {pid} {img.size}")
    return img, pid


def _gemini_tem_pessoa_v60(img):
    """Visão do Gemini com 1 modelo e timeout curto: True/False, ou None se não deu para consultar."""
    M = _m()
    chave = getattr(M, "GEMINI_API_KEY", None)
    if not chave:
        return None
    try:
        buf = io.BytesIO()
        img.convert("RGB").resize((320, 400)).save(buf, "JPEG", quality=75)
        payload = {
            "contents": [{"parts": [
                {"text": "Does this image contain any person, face, human body part, hand or human "
                         "silhouette (even blurred, dark, partial, in the background or as a portrait)? "
                         "Answer with exactly one word: SIM or NAO."},
                {"inline_data": {"mime_type": "image/jpeg", "data": base64.b64encode(buf.getvalue()).decode()}},
            ]}],
            "generationConfig": {"temperature": 0},
        }
        r = requests.post("https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent"
                          f"?key={chave}", json=payload, timeout=12)
        if r.status_code >= 400:
            return None
        partes = r.json()["candidates"][0]["content"]["parts"]
        txt = "".join(p.get("text", "") for p in partes if not p.get("thought")).strip().upper()
        if txt.startswith("SIM"):
            return True
        if txt.startswith("NAO") or txt.startswith("NÃO"):
            return False
    except Exception as e:
        print(f"[cenario] visao Gemini: {e}")
    return None


def _cenario_ronilson_v60(estilo, tema, seed):
    """Cenário validado com o MÍNIMO de chamadas: refaz (1x) só se vier pessoa ou poluição extrema."""
    M = _m()
    t0 = time.time()
    melhor = None
    for tentativa in range(2):
        if tentativa > 0 and time.time() - t0 > 25:
            break
        img, motivo = _gerar_imagem_ia(_prompt_cenario_v59(estilo, tema, seed + tentativa * 17, tentativa))
        if img is None:
            print(f"[cenario] IA falhou ({motivo})")
            break
        pessoa = _tem_rosto_haar(img)
        if not pessoa:
            pessoa = _gemini_tem_pessoa_v60(img) is True
        score = _complexidade_cenario(img)
        print(f"[cenario] tentativa {tentativa + 1}: pessoa={pessoa} poluicao={score:.1f}")
        if not pessoa and score <= 70:
            return img, None
        if melhor is None or (pessoa, score) < (melhor[0], melhor[1]):
            melhor = (pessoa, score, img)
    if melhor is not None and not melhor[0]:
        return melhor[2], None
    aviso = ("O cenario gerado tinha pessoa; usei o gradiente da paleta." if melhor is not None
             else "O cenario por IA falhou; usei o gradiente da paleta.")
    return M._gerar_fundo_gradiente(M.MARINHO, M.PETROLEO, seed), aviso


def _linha_do_chao_v60(g):
    """y da transição parede/chão a partir da luminância 2D (H,W), ou None."""
    import cv2
    perfil = cv2.GaussianBlur(g.mean(axis=1).astype(np.float32).reshape(-1, 1), (0, 0), 12).ravel()
    d = np.abs(np.diff(perfil))
    a, b = int(_H * 0.55), int(_H * 0.95)
    k = int(np.argmax(d[a:b])) + a
    return k if d[k] > 0.35 else None


def _zona_rosto_roi(a_f):
    """(x0, y0, x1, y1) de cabeça+pescoço em coordenadas da ROI (usa a forma do array)."""
    Hr, Wr = a_f.shape
    m = a_f > 0.04
    tem = m.any(axis=1)
    linhas = np.where(tem)[0]
    if len(linhas) == 0:
        return None
    esq = np.argmax(m, axis=1)
    dire = Wr - 1 - np.argmax(m[:, ::-1], axis=1)
    larg = np.where(tem, dire - esq, 0)
    y_topo = int(linhas[0])
    jan = larg[y_topo: y_topo + max(10, int(_H * 0.05))]
    ref = float(np.median(jan[jan > 0])) if np.any(jan > 0) else 0.0
    y_ombro = y_topo + int(_H * 0.16)
    if ref > 0:
        for r in range(y_topo, min(Hr, y_topo + int(_H * 0.40))):
            if larg[r] > ref * 1.5:
                y_ombro = r
                break
    y1 = max(y_topo + 20, y_ombro - 12)
    y1 = y_topo + int((y1 - y_topo) * 0.88)  # só a cabeça; o pescoço entra pela máscara de pele
    x0 = int(esq[y_topo:y1][tem[y_topo:y1]].min()) - 12
    x1 = int(dire[y_topo:y1][tem[y_topo:y1]].max()) + 12
    return max(0, x0), max(0, y_topo - 12), min(Wr, x1), min(Hr, y1)


def _integrar_v60(fundo, recorte, estilo, seed):
    """Mesma integração da v59, porém leve: reduz o recorte antes de limpar e processa só a ROI.
    Retorna (imagem RGB, corpo_inteiro, caixa_da_cabeca, info) com info = {lado, x_esq, x_dir}."""
    import cv2
    a_raw = np.asarray(recorte.split()[3])
    ys, xs = np.where(a_raw > 10)
    if len(ys) == 0:
        raise ErroEstilo("O recorte do Ronilson veio vazio.")
    recorte = recorte.crop((int(xs.min()), int(ys.min()), int(xs.max()) + 1, int(ys.max()) + 1))
    del a_raw, ys, xs
    pw0, ph0 = recorte.size
    prop = ph0 / pw0

    fundo = fundo.convert("RGB").resize((_W, _H), Image.Resampling.LANCZOS)
    fundo = fundo.filter(ImageFilter.GaussianBlur(_BLUR_CENARIO.get(estilo, 2.0)))
    gray = np.asarray(fundo.convert("L"), dtype=np.float32)
    y_chao = _linha_do_chao_v60(gray)

    corpo = prop >= 2.2
    feet_y = int(np.clip((y_chao + 0.05 * _H) if y_chao else 0.975 * _H, 0.90 * _H, 0.975 * _H))
    if corpo:
        alt = min(int(_H * 0.86), feet_y - int(_H * 0.07))
    else:
        larg_alvo = int(_W * (0.50 if prop >= 1.35 else 0.54))
        alt = min(int(larg_alvo * prop), _H)
    nw = max(1, int(alt / prop))
    y0 = feet_y - alt if corpo else _H - alt

    # reduz (com alpha pré-multiplicado) e só então limpa a borda: arrays já no tamanho final
    pes = recorte.convert("RGBa").resize((nw, alt), Image.Resampling.LANCZOS).convert("RGBA")
    del recorte
    rgb_s, a_s = _limpar_borda_v59(pes)
    del pes
    corte_esq, corte_dir = _corte_reto(a_s, "esq"), _corte_reto(a_s, "dir")

    if corte_esq and not corte_dir:
        lado, x0 = "esq", -2
    elif corte_dir and not corte_esq:
        lado, x0 = "dir", _W - nw + 2
    elif corte_esq and corte_dir:
        lado, x0 = "dir", _W - nw + 2
    else:
        lado = "dir"
        x_max = _W - nw - int(_W * 0.02)
        x_min = min(int(_W * 0.46), x_max)
        cands = sorted(set(int(v) for v in np.linspace(x_min, x_max, 4)))
        g = _pequeno_cinza(fundo)
        melhor_c = None
        for cx in cands:
            gx0, gx1 = int(cx / _W * 270), int(min(_W, cx + nw) / _W * 270)
            gy0 = int(max(0, y0) / _H * 340)
            reg = g[gy0:340, gx0:max(gx0 + 2, gx1)]
            sc = float(reg.std()) - 0.004 * (cx - x_min)
            if melhor_c is None or sc < melhor_c[0]:
                melhor_c = (sc, cx)
        x0 = melhor_c[1]

    rampa = np.ones(nw, np.float32)
    n_r = min(90, nw // 3)
    if lado == "dir" and corte_esq:
        rampa[:n_r] = np.linspace(0, 1, n_r, dtype=np.float32) ** 1.5
    elif lado == "esq" and corte_dir:
        rampa[nw - n_r:] = np.linspace(1, 0, n_r, dtype=np.float32) ** 1.5
    a_s = a_s * rampa[None, :]

    # ROI = corpo + 100px de margem (sombras e brilho de borda)
    pad = 100
    rx0, rx1 = max(0, x0 - pad), min(_W, x0 + nw + pad)
    ry0, ry1 = max(0, y0 - pad), min(_H, y0 + alt + pad)
    Wr, Hr = rx1 - rx0, ry1 - ry0
    ox, oy = x0 - rx0, y0 - ry0
    sub = np.zeros((Hr, Wr, 3), np.float32)
    a_f = np.zeros((Hr, Wr), np.float32)
    sx0, sy0 = max(0, -ox), max(0, -oy)
    dx0, dy0 = max(0, ox), max(0, oy)
    cw, ch = min(nw - sx0, Wr - dx0), min(alt - sy0, Hr - dy0)
    sub[dy0:dy0 + ch, dx0:dx0 + cw] = rgb_s[sy0:sy0 + ch, sx0:sx0 + cw]
    a_f[dy0:dy0 + ch, dx0:dx0 + cw] = a_s[sy0:sy0 + ch, sx0:sx0 + cw]
    del rgb_s, a_s

    base = np.array(fundo, dtype=np.uint8)  # cópia gravável do cenário (4MB)
    bg = base[ry0:ry1, rx0:rx1].astype(np.float32)

    ls = cv2.resize(gray, (54, 68), interpolation=cv2.INTER_AREA)
    pesos = np.clip(ls - np.percentile(ls, 40), 0, None) ** 2
    cx_luz = float((pesos * np.arange(54)[None, :]).sum() / max(pesos.sum(), 1e-3)) / 54 * _W
    luz_x = -1.0 if cx_luz < (x0 + nw / 2) else 1.0
    del gray, ls, pesos

    solido = (a_f > 0.5).astype(np.uint8)
    anel = cv2.dilate(solido, np.ones((41, 41), np.uint8)) - solido
    amb = bg[anel > 0].mean(axis=0) if anel.any() else bg.reshape(-1, 3).mean(axis=0)
    del anel

    # proteção: rosto, pescoço e mãos NÃO recebem ajuste
    orig = sub.copy()
    fm = np.zeros((Hr, Wr), np.float32)
    zr = _zona_rosto_roi(a_f)
    if zr:
        fm[zr[1]:zr[3], zr[0]:zr[2]] = 1.0
        fm = cv2.GaussianBlur(fm, (0, 0), 5)
    ycc = cv2.cvtColor(np.clip(sub, 0, 255).astype(np.uint8), cv2.COLOR_RGB2YCrCb)
    Yc, Cr, Cb = ycc[..., 0].astype(np.int16), ycc[..., 1].astype(np.int16), ycc[..., 2].astype(np.int16)
    del ycc
    R, G, B = sub[..., 0], sub[..., 1], sub[..., 2]
    pele = ((Cr >= 135) & (Cr <= 173) & (Cb >= 77) & (Cb <= 120) & (Yc > 45) & (Yc < 235)
            & (R > G) & (G >= B - 3) & ((R - B) > 18) & (a_f > 0.5)).astype(np.uint8)
    del Yc, Cr, Cb
    pele = cv2.morphologyEx(pele, cv2.MORPH_OPEN, np.ones((3, 3), np.uint8))
    pele = cv2.morphologyEx(pele, cv2.MORPH_CLOSE, np.ones((9, 9), np.uint8))
    n_c, lab, st, _ = cv2.connectedComponentsWithStats(pele)
    area_corpo = max(int(solido.sum()), 1)
    for k in range(1, n_c):
        if st[k, cv2.CC_STAT_AREA] > 0.06 * area_corpo:
            comp = lab == k
            if not (fm[comp] > 0.3).any():  # mancha grande fora do rosto = roupa; rosto+pescoço ficam
                pele[comp] = 0
    del lab
    pele = cv2.GaussianBlur(pele.astype(np.float32), (0, 0), 2)
    nucleo_f = cv2.GaussianBlur(cv2.erode(a_f, np.ones((7, 7), np.uint8)), (0, 0), 1.5)
    protege = (np.clip(np.maximum(fm, pele), 0, 1) * np.clip(nucleo_f * 1.4, 0, 1))[..., None]
    del fm, pele, nucleo_f

    # 1) roupa/corpo: cor e exposição da cena + nível de preto
    media = sub[solido > 0].mean(axis=0)
    ganho = (amb / max(amb.mean(), 1)) / (media / max(media.mean(), 1))
    ganho = np.clip(1 + 0.42 * (ganho - 1), 0.78, 1.22)
    expo = float(np.clip((amb.mean() + 55) / (media.mean() + 55), 0.58, 1.08))
    sub *= (ganho * (expo ** 0.85)).astype(np.float32)
    cinza = sub.mean(axis=2, keepdims=True)
    mx, mn = sub.max(axis=2, keepdims=True), sub.min(axis=2, keepdims=True)
    k_sat = 0.22 * np.clip((mx - mn) / (mx + 1.0) - 0.22, 0, 1)
    sub = sub * (1 - k_sat) + cinza * k_sat
    del cinza, mx, mn, k_sat
    bg_suave = cv2.GaussianBlur(bg, (0, 0), 20)
    sub = sub * 0.94 + bg_suave * 0.06

    # 2) luz direcional suave
    t = np.clip((np.arange(Wr, dtype=np.float32)[None, :] - ox) / max(nw, 1), 0, 1)
    t = t if luz_x > 0 else 1 - t
    sub *= (1.04 - 0.12 * t)[..., None]
    sub *= (1.0 - 0.05 * (np.arange(ry0, ry1, dtype=np.float32) / (_H - 1)))[:, None, None]

    # 3) borda: absorve a cor do cenário + contorno de luz discreto
    n4 = cv2.GaussianBlur(cv2.erode(a_f, np.ones((9, 9), np.uint8)), (0, 0), 2)
    n2 = cv2.GaussianBlur(cv2.erode(a_f, np.ones((5, 5), np.uint8)), (0, 0), 1)
    b4 = np.clip(a_f - n4, 0, 1)[..., None]
    b2 = np.clip(a_f - n2, 0, 1)[..., None]
    s_e = np.clip(0.20 * b4 + 0.32 * b2, 0, 0.55)
    sub = sub * (1 - s_e) + bg_suave * s_e
    lado_luz = np.clip(1 - t * 2.0, 0, 1)[..., None]
    rim = np.array([255, 205, 130], np.float32) * 0.5 + amb * 0.6
    sub = sub + 0.12 * b4 * lado_luz * rim * (1 - sub / 255.0)
    del n4, n2, b4, b2, s_e, bg_suave
    sub = sub * (1 - protege) + orig * protege
    del orig

    # 4) sombras: projetada curta + contato POR PÉ
    sil = cv2.GaussianBlur(a_f, (0, 0), 14)
    sombra = cv2.warpAffine(sil, np.float32([[1, 0, -luz_x * 42], [0, 1, 12]]), (Wr, Hr))
    sombra = sombra * (1 - np.clip(cv2.GaussianBlur(a_f, (0, 0), 2), 0, 1))
    del sil
    if corpo:
        chao = np.zeros((Hr, Wr), np.float32)
        base_y = oy + alt
        banda_h = max(12, int(alt * 0.07))
        yb0 = max(0, base_y - banda_h)
        faixa = (a_f[yb0:min(Hr, base_y)] > 0.35).astype(np.uint8)
        n_f, _, st_f, cen_f = cv2.connectedComponentsWithStats(faixa)
        pes_l = [(int(cen_f[k][0]), yb0 + st_f[k, cv2.CC_STAT_TOP] + st_f[k, cv2.CC_STAT_HEIGHT],
                  int(st_f[k, cv2.CC_STAT_WIDTH])) for k in range(1, n_f) if st_f[k, cv2.CC_STAT_AREA] >= 40]
        if pes_l:
            y_max = max(p[1] for p in pes_l)
            for xk, ylow, wk in pes_l:
                dif = y_max - ylow
                yy_s = ylow - 2 if dif <= 10 else ylow + int(0.6 * dif) + 3
                forca = 1.0 if dif <= 10 else 0.65
                cv2.ellipse(chao, (xk, yy_s), (int(max(24, wk * 0.8)), int(_H * 0.011) + 4), 0, 0, 360, forca, -1)
        else:
            cv2.ellipse(chao, (ox + nw // 2, base_y - 4), (int(nw * 0.4), int(_H * 0.012) + 4), 0, 0, 360, 1.0, -1)
        chao = cv2.GaussianBlur(chao, (0, 0), 10)
        sombra = np.clip(sombra + 0.8 * chao, 0, 1)
        degrade = np.clip((np.arange(Hr, dtype=np.float32) - (base_y - 30)) / 160.0, 0, 1)
        bg = bg * (1 - 0.16 * degrade)[:, None, None]
        del chao, degrade
    s = (0.32 * sombra)[..., None]
    bg = bg * (1 - s) + (amb * 0.20) * s
    del sombra, s

    # 5) composição na ROI; grão e correção de cor da cena NÃO entram no rosto/mãos
    out = bg * (1 - a_f[..., None]) + sub * a_f[..., None]
    del bg, sub
    sem_grao = np.clip(out, 0, 255).astype(np.uint8)
    del out
    base[ry0:ry1, rx0:rx1] = sem_grao
    rng = np.random.RandomState(int(seed) % 100000)
    for r0 in range(0, _H, 225):
        r1 = min(_H, r0 + 225)
        ruido = rng.normal(0, 2.4, (r1 - r0, _W, 1)).astype(np.float32)
        base[r0:r1] = np.clip(base[r0:r1].astype(np.float32) + ruido, 0, 255).astype(np.uint8)
    graduada = np.asarray(_grade_estilo(Image.fromarray(base), "cinematic" if estilo == "cinematic" else "showcase"))
    del base
    final = np.array(graduada, dtype=np.uint8)
    P = protege[..., 0] * a_f
    P3 = P[..., None]
    gr_roi = graduada[ry0:ry1, rx0:rx1].astype(np.float32)
    final[ry0:ry1, rx0:rx1] = np.clip(gr_roi * (1 - P3) + sem_grao.astype(np.float32) * P3, 0, 255).astype(np.uint8)
    del gr_roi, graduada, sem_grao, protege, P3
    img = Image.fromarray(final)

    # geometria para o título (coordenadas do card)
    r0, r1 = max(0, int(_H * 0.35) - ry0), min(Hr, int(_H * 0.92) - ry0)
    cols = np.where((a_f[r0:r1] > 0.3).any(axis=0))[0] if r1 > r0 else []
    info = {"lado": lado,
            "x_esq": int(cols.min()) + rx0 if len(cols) else x0,
            "x_dir": int(cols.max()) + rx0 if len(cols) else x0 + nw}
    cab = _caixa_cabeca(a_f)
    if cab:
        cab = (max(0, cab[0] + rx0), max(0, cab[1] + ry0), min(_W, cab[2] + rx0), min(_H, cab[3] + ry0))
    return img, corpo, cab, info


# v68: poses com gesto solto (dedos levantados, dedo na testa, apontando) nao combinam com o tema -> sorteia outra foto
_cache_pose = {}  # public_id -> True se a pose tem gesto


def _pose_tem_gesto(img, pid):
    """Visao do Gemini (1 chamada por foto, com cache em memoria). Falha/sem chave = considera neutra."""
    if pid in _cache_pose:
        return _cache_pose[pid]
    M = _m()
    chave = getattr(M, "GEMINI_API_KEY", None)
    if not chave:
        return False
    try:
        rgba = img.convert("RGBA")
        fundo_c = Image.new("RGB", rgba.size, (200, 200, 200))
        fundo_c.paste(rgba, mask=rgba.split()[3])
        fundo_c.thumbnail((360, 480))
        buf = io.BytesIO()
        fundo_c.save(buf, "JPEG", quality=75)
        payload = {
            "contents": [{"parts": [
                {"text": "Look only at the person's hands and arms. Answer with exactly one word: GESTO if a hand is "
                         "raised, fingers are counting or pointing, a hand is raised to the forehead/temple, the palm is "
                         "presented or waving; NEUTRO if the arms are down, crossed, in pockets, resting, the hand rests "
                         "on the chin, or the person holds an object naturally (tablet, pen, glasses)."},
                {"inline_data": {"mime_type": "image/jpeg", "data": base64.b64encode(buf.getvalue()).decode()}},
            ]}],
            "generationConfig": {"temperature": 0},
        }
        r = requests.post("https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent"
                          f"?key={chave}", json=payload, timeout=12)
        if r.status_code >= 400:
            return False
        partes = r.json()["candidates"][0]["content"]["parts"]
        txt = "".join(p.get("text", "") for p in partes if not p.get("thought")).strip().upper()
        resultado = txt.startswith("GESTO")
        _cache_pose[pid] = resultado
        print(f"[ronilson] pose {pid}: {'GESTO' if resultado else 'neutra'}")
        return resultado
    except Exception as e:
        print(f"[ronilson] classificacao de pose ignorada: {e}")
        return False


def _carregar_recorte_neutro():
    """Sorteia uma foto; se a pose tem gesto solto, sorteia outra (ate 4 tentativas)."""
    ultimo = None
    for _ in range(4):
        recorte, pid = _carregar_recorte_ronilson_v60()
        ultimo = (recorte, pid)
        if not _pose_tem_gesto(recorte, pid):
            return recorte, pid
        print(f"[ronilson] pose com gesto ({pid}); sorteando outra")
    return ultimo


def _clarear_cenario(img):
    """v66: cenario escuro demais (o Gemini ignora 'claro') ganha luz: eleva a mediana e o preto, sem estourar."""
    try:
        a = np.asarray(img.convert("RGB"), dtype=np.float32) / 255.0
        lum_d = a[:, int(a.shape[1] * 0.40):].mean(axis=2)  # area onde o corpo fica (60% da direita)
        med = float(np.median(lum_d))
        if med >= 0.30:
            return img
        g = float(np.clip(np.log(0.30) / np.log(max(med, 0.02)), 0.55, 1.0))
        a = 0.07 + np.power(a, g) * 0.93
        print(f"[cenario] escuro (mediana {med:.2f}); clareado com gamma {g:.2f}")
        return Image.fromarray((np.clip(a, 0, 1) * 255).astype(np.uint8))
    except Exception as e:
        print(f"[cenario] clarear ignorado: {e}")
        return img


def _responder_com_ronilson(M, tema, legenda, erros_leg, estilo, seed):
    """Card = cenário por estilo/tema + Ronilson (ronilson_sem_fundo) integrado + título."""
    rotulo = ESTILOS[estilo]["rotulo"] if estilo in ESTILOS else "Automático"
    aviso = None
    try:
        _ETAPA["v"] = "escolher recorte do Ronilson"
        recorte, pid = _carregar_recorte_neutro()
        _ETAPA["v"] = "gerar cenario"
        fundo, aviso = _cenario_ronilson(estilo, tema, seed)
        fundo = _clarear_cenario(fundo)
        _ETAPA["v"] = "integrar o Ronilson ao cenario"
        img, em_pe, cabeca, x_esq, lado_x, x_dir = _integrar_v58(fundo, recorte, estilo, seed)
        try:
            haar = M._detectar_rosto(img)
            if haar:
                cabeca = haar
        except Exception as e:
            print(f"[ronilson] Haar ignorado: {e}")
        _ETAPA["v"] = "montar o card (titulo/layout)"
        cor_dest, cor_fundo_txt = M._escolher_cor_destaque(seed)
        # v67: tamanho do bloco do titulo normalizado (~44% da largura do card), com mais respiro entre linhas
        _margem = getattr(M, "SAFE_MARGIN", 80)
        if lado_x == "esq":  # corpo encostado na esquerda: o titulo comeca depois dele
            x_texto = int(min(_W * 0.62, x_dir + 36))
            disponivel = int(max(300, _W - x_texto - 70))
        else:
            x_texto = None
            disponivel = int(max(300, x_esq - _margem - 28))
        max_px = int(max(340 if x_texto is None else 300, min(520, disponivel)))
        escala = max(0.72, min(0.95, 0.72 * max_px / 352.0))
        _kw = dict(cor_dest=cor_dest, cor_fundo_txt=cor_fundo_txt, cor_overlay=None, tem_pessoa=True,
                   em_pe=em_pe, cabeca_bbox=cabeca, respiro=1.24, gap_fator=0.22, x_texto=x_texto)
        try:  # passada de medicao: o motor desenha, medimos a largura real do bloco e corrigimos a escala
            alvo = min(int(_W * 0.44), disponivel)
            teste, _ = M.desenhar_titulo(img, tema, seed, max_px_pessoa=max_px, escala_pessoa=escala, **_kw)
            dif = np.abs(np.asarray(teste.convert("RGB"), dtype=np.int16)
                         - np.asarray(img.convert("RGB"), dtype=np.int16)).max(axis=2) > 45
            if lado_x == "esq":
                dif[:, :max(0, x_texto - 10)] = False  # so a area do texto (a direita), nunca o corpo
            else:
                dif[:, max(0, x_esq - 10):] = False  # so a area do texto, nunca o corpo
            cols = np.where(dif.any(axis=0))[0]
            del teste, dif
            if len(cols) > 20:
                largura = int(cols.max() - cols.min())
                fator = alvo / max(largura, 1)
                if fator < 0.88 or fator > 1.10:
                    escala = float(np.clip(escala * fator, 0.55, 1.12))
                    max_px = int(min(disponivel, max(300, alvo + 40)))
                    print(f"[titulo] bloco {largura}px -> alvo {alvo}px; escala {escala:.2f}")
        except Exception as e:
            print(f"[titulo] normalizacao ignorada: {e}")
        card, _ = M.desenhar_titulo(img, tema, seed, max_px_pessoa=max_px, escala_pessoa=escala, **_kw)
        card_id = f"preview_{uuid.uuid4().hex[:10]}"
        saida = io.BytesIO()
        card.save(saida, format="JPEG", quality=93)
        card_bytes = saida.getvalue()
        M._cards_pendentes[card_id] = {
            "tema": tema, "legenda": legenda, "imagem_fundo": "",
            "pid_fundo": f"ronilson_sem_fundo:{estilo}:{pid}", "card_bytes": card_bytes,
        }
    except ErroEstilo as e:
        return jsonify({"erro": f"Com Ronilson ({rotulo}): {e}"}), 502
    except Exception as e:
        traceback.print_exc()
        return jsonify({"erro": f"Erro Com Ronilson ({rotulo}) (etapa: {_ETAPA['v']}): "
                                f"{type(e).__name__}: {str(e)[:200]}"}), 500
    resp = {
        "card_id": card_id,
        "preview_url": f"data:image/jpeg;base64,{base64.b64encode(card_bytes).decode()}",
        "legenda": legenda, "imagem_fundo": "", "foto_ronilson": pid,
    }
    if erros_leg:
        resp["aviso_legenda"] = erros_leg
    if aviso:
        resp["aviso_estilo"] = aviso
    return jsonify(resp)


@bp.route("/preview-card-estilo", methods=["POST"])
def rota_preview_card_estilo():
    import cloudinary.uploader

    M = _m()

    data = request.get_json() or {}
    tema = data.get("tema", "").strip()
    legenda = data.get("legenda", "").strip()
    estilo = (data.get("estilo") or "").strip().lower()
    if not tema:
        return jsonify({"erro": "Tema obrigatorio"}), 400
    com_ronilson = bool(data.get("com_ronilson"))  # v57: foto sem fundo do Ronilson integrada ao cenario
    if com_ronilson and estilo in ("", "auto"):
        estilo = "auto"
    elif estilo not in ESTILOS:
        return jsonify({"erro": "Estilo invalido"}), 400

    # Legenda: mesmo tratamento do /preview-card
    erros_leg = None
    if not legenda:
        try:
            legenda = M.gerar_legenda_ia(tema)
        except Exception as e:
            erros_leg = str(e)
            legenda = ""
    if legenda and "CRP 04/57327" not in legenda:
        legenda = legenda.rstrip() + M.ASSINATURA

    seed = M._seed_variavel(tema, data.get("seed"))
    print(f"[estilo] tema='{tema}' estilo='{estilo}' seed={seed}")

    if com_ronilson:  # v57: caminho novo; os demais estilos seguem abaixo, intactos
        return _responder_com_ronilson(M, tema, legenda, erros_leg, estilo, seed)

    tmp_pid = ""
    _ETAPA["v"] = "gerar imagem-base"
    try:
        base, aviso = _base_cena(estilo, seed, tema, data.get("variante"))

        # Envia a base como arquivo temporário no Cloudinary para usar o motor de tipografia
        _ETAPA["v"] = "upload temporario no Cloudinary"
        buf = io.BytesIO()
        base.convert("RGB").save(buf, format="JPEG", quality=95)
        buf.seek(0)
        res = cloudinary.uploader.upload(
            buf,
            public_id=f"{M.CLOUDINARY_PREVIEW}/estilo_tmp_{uuid.uuid4().hex[:10]}",
            resource_type="image",
            overwrite=True,
        )
        url_tmp = res.get("secure_url", "")
        tmp_pid = res.get("public_id", "")
        if not url_tmp:
            raise ErroEstilo("Falha ao preparar a imagem do estilo (upload temporario).")

        _ETAPA["v"] = "montar o card (titulo/layout)"
        card = None
        if _TITULO_INTELIGENTE and estilo in _ESTILOS_COM_PESSOA:
            try:
                card = _card_titulo_inteligente(M, base, tema, seed)
            except Exception as e:
                print(f"[estilo] titulo inteligente falhou, usando o caminho padrao: {e}")
                card = None
        if card is None:
            card = M.gerar_card_imagem(tema, legenda, url_tmp, tmp_pid, seed=seed)

        card_id = f"preview_{uuid.uuid4().hex[:10]}"
        saida = io.BytesIO()
        card.save(saida, format="JPEG", quality=93)
        card_bytes = saida.getvalue()
        preview_url = f"data:image/jpeg;base64,{base64.b64encode(card_bytes).decode()}"
        M._cards_pendentes[card_id] = {
            "tema": tema,
            "legenda": legenda,
            "imagem_fundo": "",
            "pid_fundo": f"estilo:{estilo}",
            "card_bytes": card_bytes,
        }
    except ErroEstilo as e:
        return jsonify({"erro": f"Estilo {ESTILOS[estilo]['rotulo']}: {e}"}), 502
    except Exception as e:
        traceback.print_exc()
        return (
            jsonify(
                {
                    "erro": f"Erro no estilo {ESTILOS[estilo]['rotulo']} "
                    f"(etapa: {_ETAPA['v']}): {type(e).__name__}: {str(e)[:200]}"
                }
            ),
            500,
        )
    finally:
        if tmp_pid:
            try:
                cloudinary.uploader.destroy(tmp_pid)
            except Exception as e:
                print(f"[estilo] nao apagou temporario {tmp_pid}: {e}")

    resp = {
        "card_id": card_id,
        "preview_url": preview_url,
        "legenda": legenda,
        "imagem_fundo": "",
    }
    if erros_leg:
        resp["aviso_legenda"] = erros_leg
    if _ETAPA.get("variante") and _ETAPA["variante"] != "-":
        resp["variante"] = _ETAPA["variante"]
    if aviso:
        resp["aviso_estilo"] = aviso
    return jsonify(resp)
