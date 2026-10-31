"""
python-api/estilos_extras_v73.py  —  v73  —  mais variações DENTRO de cada estilo (nada preso a um único objeto)

1) EXTRAS_FAMILIAS: famílias novas, mais livres e menos literais, para os estilos que já existiam
   (ex.: Kintsugi deixa de ser sempre porcelana: parede, madeira, vidro, ferramenta, papel, luz...).
2) ESTILOS_V73: Cinematic e Showcase entram no mesmo rodízio (antes só alternavam a variante de rosto).
Mesclado em estilos_prompts_v71.ESTILOS_V71 no fim daquele arquivo.
"""

EXTRAS_FAMILIAS = {
    "gold": {
        "arquitetura_reparada": {"g": "tristeza recomeco vazio tensao", "s": (
            "a weathered plaster wall with one long crack filled with gold leaf, one side lit by the morning sun",
            "a cracked stone step with fissures traced in gold and a tiny fern growing beside it",
            "an old wooden door panel split along the grain and mended with gold lines",
            "a brick wall where one stretch of mortar lines glows gold, the rest left plain",
        )},
        "organico_reparado": {"g": "recomeco tristeza autoestima novo_dia", "s": (
            "a walnut shell split and rejoined with gold, resting on dark wood",
            "a broken branch splinted with gold thread and one small new leaf at its tip",
            "a feather with a torn vane repaired with fine gold lines, on pale linen",
            "a dry seed pod cracked open and joined with gold, a green shoot beside it",
        )},
        "vidro_e_luz": {"g": "visto tristeza recomeco novo_dia", "s": (
            "a cracked window pane whose fractures are filled with gold, dawn light glowing behind it",
            "a glass sphere with a fracture mended in gold, warm light gathered inside",
            "a mosaic of glass shards held by thin gold lines like a small stained-glass panel",
        )},
        "luz_como_kintsugi": {"g": "tristeza vazio recomeco novo_dia", "s": (
            "a thin vertical line of warm sunrise light between two dark curtains, like a gold seam in the dark",
            "golden light drawing lines across cracked dry earth, a single green sprout at a junction",
            "a ribbon of golden light crossing the gap between two stone slabs on a dark floor",
        )},
        "papel_e_livros": {"g": "tristeza vinculo visto recomeco", "s": (
            "a torn blank page joined with a seam of gold ink, soft light, no writing",
            "a book with a cracked cloth spine bound with gold thread, closed, on a wooden table",
        )},
        "metal_e_tempo": {"g": "tensao autoestima recomeco visto", "s": (
            "an old brass key snapped and rejoined with gold, resting on dark linen",
            "a vintage clock face with a hairline crack mended in gold, hands still",
            "a small tarnished metal cup dented and mended with gold lines",
        )},
    },
    "portal": {
        "aberturas_de_luz": {"g": "recomeco novo_dia vazio tristeza", "s": (
            "a gap in a dense green hedge revealing golden dawn light, a small stone path leading into it",
            "an opening between two large smooth rocks revealing a soft sunrise",
            "a rectangle of dawn light projected on a dark wall like a door of light, the floor in shadow",
            "a break in the clouds above a quiet field forming a doorway of light",
        )},
    },
    "macro": {
        "texturas_inesperadas": {"g": "visto tensao tristeza autoestima", "s": (
            "layers of peeling paint in teal, navy and cream, each layer sharply lit",
            "a rusted metal edge with a single flake of gold leaf catching the light",
            "the grain of an old wooden table with a warm line of light crossing it",
            "ink drying on blank paper, the edge forming a fine delicate coastline",
            "a salt crust forming tiny crystals on dark stone, one glinting orange",
        )},
    },
    "floating": {
        "elementos_do_ar": {"g": "novo_dia vazio recomeco tensao", "s": (
            "soap bubbles of different sizes catching dawn colors, slowly rising, one pierced by light",
            "a few feathers, a leaf and a thread of golden dust drifting upward in a gentle spiral",
            "paper petals and a tiny glass bead hovering in a soft ring of light",
        )},
    },
    "museum": {
        "arquitetura_como_obra": {"g": "visto autoestima novo_dia vazio", "s": (
            "a spiral staircase seen from below as if it were a sculpture, light spiralling with it",
            "a plain arched niche in a gallery wall holding a single soft pool of light",
            "a long empty bench-free gallery floor with one warm rectangle of light, like a painting on the ground",
        )},
    },
    "smoke": {
        "calor_e_vapor": {"g": "tensao tristeza vinculo recomeco", "s": (
            "steam from a freshly poured pot of tea dissolving into a window beam of light",
            "warm steam rising from a ceramic bowl in cool blue light, thinning as it climbs",
            "a thin ribbon of smoke from a snuffed wick drawing an unhurried curve",
        )},
    },
}


ESTILOS_V73 = {
    # ───────────────────────── CINEMATIC ─────────────────────────
    "cinematic": {
        "rotulo_sujeito": "SETTING AND MOOD (follow it closely; a person may appear only as the Subject directive above allows)",
        "regra": (
            "Premium film-still quality: physically plausible light, authentic texture, no stock-photo look, no "
            "CGI sheen, never gloomy. Keep generous calm space in the upper-left third for typography."
        ),
        "conceito": (
            "a sophisticated cinematic film still, film composition, professional framing, immersive atmosphere, "
            "realistic texture, elegant tones, soft shadows, premium photographic appearance, cinematic lens, subtle "
            "bokeh, balanced contrast, authentic photographic realism, without artificial appearance"
        ),
        "luz": (
            "dramatic yet natural cinematic lighting with soft volumetric light",
            "blue hour fading into a warm sunrise, long soft shadows",
            "soft morning backlight through sheer curtains with a faint haze",
            "a single warm practical light against cool teal ambience",
            "gentle overcast light with warm highlights",
        ),
        "familias": {
            "interiores_quietos": {"g": "visto vazio tristeza vinculo", "s": (
                "a quiet apartment living room at dawn, a warm lamp still on and cool blue window light, a mug on a low table",
                "a long kitchen table by a window at sunrise with two cups, steam rising, shallow focus",
                "a bedroom with sheer curtains lifting in the morning breeze, crisp linen, a golden stripe of sun",
                "a study with bookshelves and a desk lamp glowing, rain on the window, calm and warm",
            )},
            "exteriores_ao_amanhecer": {"g": "recomeco novo_dia autoestima vazio", "s": (
                "a quiet city street at first light with warm window lights and a blue sky",
                "a hillside path at sunrise with long shadows and a glowing horizon",
                "a rooftop terrace at dawn with a softly blurred skyline and a few potted plants",
                "a garden at golden hour with backlit leaves and warm haze",
            )},
            "detalhes_e_objetos": {"g": "visto tensao vinculo tristeza", "s": (
                "a cup of tea steaming in backlight, shallow depth of field, a quiet room behind",
                "an open window with a moving curtain, dust motes glowing in the beam",
                "keys on a wooden table by an entrance door, warm light, a plant beside them",
                "an unlit candle and a box of matches on a wooden shelf in blue light",
            )},
            "natureza_e_luz": {"g": "novo_dia recomeco tristeza vazio", "s": (
                "light rays through tall trees in a misty forest, a quiet path below",
                "a field of tall grass backlit at sunrise, soft drifting seeds",
                "a single tree on a hill silhouetted against a glowing sky",
                "leaves moving in warm backlight, soft dappled shadows",
            )},
            "clima_e_vidro": {"g": "tristeza tensao vazio visto", "s": (
                "rain on a window with a warm light glowing behind the glass",
                "fog on a window pane with one cleared patch showing a soft dawn",
                "a window with condensation and a small plant on the sill, early light",
            )},
        },
        "atmo": (
            "slow, quiet and intimate", "hushed, expectant, the night ending", "warm and human, never staged",
            "soft, contemplative, gently hopeful",
        ),
        "comp": (
            "35mm lens, shallow depth of field", "50mm lens at eye level", "85mm compression with soft background",
            "wide frame with the subject small and space around it",
        ),
    },
    # ───────────────────────── SHOWCASE ─────────────────────────
    "showcase": {
        "rotulo_sujeito": "SETTING AND SUBJECT (follow it closely; a person may appear only as the Subject directive above allows)",
        "regra": (
            "Premium campaign-quality finish but intimate and human, never an advertising or real-estate look: clean "
            "composition, calm backdrop, no stock-photo feel. Keep generous calm space in the upper-left third for typography."
        ),
        "conceito": (
            "a premium showcase presentation of one symbolic element, clean and sophisticated composition, absolute focus "
            "on the central subject, carefully positioned studio-quality light, an elegant discreet background, sharp "
            "details, elevated realism and a balanced visual composition"
        ),
        "luz": (
            "soft window key light with gentle warm fill",
            "diffused daylight with a faint warm rim",
            "a single soft spot of light with a smooth falloff",
            "side-light that models the surface and texture",
        ),
        "familias": {
            "objeto_unico": {"g": "autoestima visto vinculo recomeco", "s": (
                "a single ceramic vase holding a few sage branches, on a pale surface with soft window light",
                "a handmade cup on a wooden tray, a still-life with quiet shadows",
                "a smooth stone sphere on a wooden plinth, soft light from the left",
                "a small brass key resting on dark linen, a single warm glint",
            )},
            "botanico_de_estudio": {"g": "recomeco novo_dia tristeza autoestima", "s": (
                "a bunch of eucalyptus in a glass vase against a deep teal wall",
                "a single flower stem in a plain bottle on pale linen, soft shadow",
                "a small potted plant on a windowsill, premium editorial styling",
                "a branch with a few young leaves in a simple jar, backlit",
            )},
            "texturas_e_tecidos": {"g": "vinculo tensao visto tristeza", "s": (
                "folded natural linen and a sprig of sage, seen from above in soft light",
                "a knitted blanket texture in cream and teal with a thin gold thread, soft raking light",
                "a stack of plain cream paper sheets with a pen on top, soft window light",
            )},
            "arquitetura_minima": {"g": "visto vazio autoestima novo_dia", "s": (
                "a plain arch and a plaster wall with a soft long shadow and one warm patch of light",
                "a wall niche holding a single object in a pool of soft light",
                "a smooth curved wall with a single band of sunrise light crossing it",
            )},
            "luz_como_produto": {"g": "novo_dia recomeco visto vazio", "s": (
                "a prism splitting a soft dawn ray into a gentle spectrum on a pale wall",
                "a beam of warm light crossing a plain plinth like a spotlight on nothing",
                "a glass of clear water on a table throwing a soft golden caustic across wood",
            )},
        },
        "atmo": (
            "calm, refined, quietly premium", "intimate and human, not commercial", "silent and elegant",
        ),
        "comp": (
            "centered and calm", "the subject low in the frame with generous empty space above",
            "a three-quarter angle with soft depth", "a close crop with shallow depth of field",
        ),
    },
}
