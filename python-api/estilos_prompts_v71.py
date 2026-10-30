"""
python-api/estilos_prompts_v71.py  —  v71  —  Prompts extensos e ALTERNADOS para os 7 estilos poéticos

Estilos: gold (Kintsugi), smoke (Fumaça), portal (Portal), ice (Gelo), floating (Flutuante),
         macro (Macro) e museum (Museu).

Problema anterior: o prompt sempre carregava a descrição literal do estilo ("gota na folha", "gelo derretendo")
junto com um banco pequeno de variações sorteado pela seed (que podia repetir). Resultado: posts parecidos.

Como funciona agora (só texto de prompt; zero custo extra de chamadas/memória):
  1. cada estilo tem um CONCEITO neutro e detalhado (a essência/metáfora, sem objeto literal fixo);
  2. cada estilo tem FAMÍLIAS de sujeitos (ex. Macro: fios e tecidos, mineral, botânico, objetos de cuidado,
     luz e óptica, vida minúscula) e cada família tem vários sujeitos;
  3. as famílias entram em RODÍZIO (baralho embaralhado: só repete depois de passar por todas), preferindo as
     que combinam com a leitura psicológica do tema (visto, recomeço, vazio, tensão, vínculo, tristeza...);
  4. dentro da família, o sujeito também roda em baralho; fundo, enquadramento, atmosfera, cor e luz idem.

Chamado por estilos_card._prompt (flag _PROMPTS_V71). Se algo falhar, o fluxo antigo é usado.
"""
import random

_FILAS = {}
_ULTIMO = {}


def _baralho(chave, n):
    """Índice sorteado sem repetir até esgotar todas as opções (e sem repetir na virada do baralho)."""
    if n <= 1:
        return 0
    fila = _FILAS.get(chave)
    if not fila:
        fila = list(range(n))
        random.shuffle(fila)
        if _ULTIMO.get(chave) == fila[-1]:
            fila[0], fila[-1] = fila[-1], fila[0]
        _FILAS[chave] = fila
    i = fila.pop()
    _ULTIMO[chave] = i
    return i


# Cor / paleta: acentos de cor que alternam (a paleta base já vai no prompt principal)
_COR = (
    "deep navy shadows with solar orange as the single warm accent",
    "petroleum teal dominant, sage midtones and one thin line of orange light",
    "sage and snow-white haze dominant, calm and airy, orange only as a tiny glint",
    "a navy-to-teal gradient with a soft cream highlight",
    "teal and sage with warm gold highlights",
    "mostly petroleum teal and navy, the orange light entering from one side only",
)

_ROTULOS = (
    ("onde", "Setting / surface"),
    ("fora", "Beyond the opening"),
    ("comp", "Framing"),
    ("atmo", "Atmosphere"),
)

_REGRA_GERAL = (
    "Premium editorial campaign quality: physically plausible materials, rich micro-texture, natural light "
    "falloff, no stock-photo look, no clip-art, no CGI sheen. No people, faces, hands or body parts anywhere in "
    "the frame. Keep generous calm negative space, especially in the upper-left third."
)

ESTILOS_V71 = {
    # ───────────────────────────── KINTSUGI ─────────────────────────────
    "gold": {
        "conceito": (
            "a fine-art still life of kintsugi as a metaphor for healing, trauma, grief and starting again: "
            "something that was broken is whole again and the repair is the most beautiful part. Luminous gold "
            "seams are the hero, rendered as real gold lacquer with a subtle metallic sheen and tiny natural "
            "irregularities, never a flat yellow line. The mended piece is matte, handmade and imperfect, in the "
            "clinic palette"
        ),
        "luz": (
            "soft dawn side-light from the left with warm solar-orange glints running along the gold",
            "warm window light with a gentle shadow, the gold seams catching small sparks",
            "backlit rim light that makes the edges and the gold glow",
            "diffused overcast morning light with warm glints on the gold",
            "a low raking light that makes the gold seams stand out in relief",
        ),
        "familias": {
            "louca": {
                "g": "tristeza recomeco autoestima novo_dia",
                "s": (
                    "a wide handmade chawan tea bowl in matte petroleum-teal glaze, mended with bold branching gold seams like rivers on a map",
                    "a tall narrow vase in deep navy glaze with one dramatic gold-filled crack spiralling from lip to base",
                    "a shallow sage-green plate cracked into several pieces and rejoined, the gold lines forming a calm irregular mosaic",
                    "a small round teapot in dusty navy whose broken spout is reattached in gold, a faint curl of steam still rising",
                    "a delicate cup with a gold-mended handle, its glaze finely crazed, resting on its saucer",
                ),
            },
            "natureza_reparada": {
                "g": "tristeza recomeco vazio novo_dia",
                "s": (
                    "a smooth river stone split in two and rejoined along a thin gold line, lying on dark moss",
                    "a dried autumn leaf with every torn vein traced in gold, laid flat on pale stone",
                    "a weathered terracotta pot cracked open and mended in gold, a fresh green shoot rising through the seam",
                    "dry cracked earth whose fissures are filled with gold leaf, one tiny sprout emerging at a junction",
                    "a slice of tree trunk with its natural splits filled with gold, growth rings visible, on a dark wooden table",
                ),
            },
            "objeto_cotidiano": {
                "g": "visto vinculo tensao autoestima",
                "s": (
                    "a glass tumbler cracked and mended with gold lacquer, the seam catching the light like a drawn river",
                    "a plain porcelain plate in two halves joined by a single confident gold line, seen top-down on linen",
                    "a small mirror with a hairline fracture filled with gold, reflecting only a soft glow of dawn",
                    "two mismatched ceramic cups, each mended in gold, standing side by side",
                    "a wooden bowl split by age and joined with gold, the grain clearly visible",
                ),
            },
            "tecido_e_fio": {
                "g": "tensao vinculo tristeza recomeco",
                "s": (
                    "a torn piece of natural linen stitched back together with golden thread in a visible sashiko-style repair",
                    "a frayed teal woven ribbon with a gold thread mending the break",
                    "a worn leather notebook cover with a split spine repaired with gold stitching",
                    "a knotted ball of teal yarn whose tangle resolves into a single gold thread leading out of the frame",
                ),
            },
            "escala_e_detalhe": {
                "g": "visto tristeza autoestima novo_dia",
                "s": (
                    "an extreme close-up of one gold seam crossing a crackled glaze, each tiny crack catching a spark of warm light",
                    "a bowl seen top-down where the gold seams read like rivers on a map, a single tea leaf resting beside it",
                    "a shard lit from behind, its gold edge glowing like a coastline, other pieces softly out of focus",
                    "a vase in the middle of being reassembled: pieces nearly joined, one gap still open, gold lacquer drying at the seam",
                ),
            },
            "ritual_de_cuidado": {
                "g": "vinculo visto recomeco novo_dia vazio",
                "s": (
                    "a mended bowl on a low wooden tray beside a small spoon of matcha and a wisp of steam, tea-ceremony stillness",
                    "a mended cup beside an open empty notebook and a pencil, as if someone is about to begin",
                    "a mended vase holding a single sage branch on a windowsill at dawn",
                    "a mended bowl holding a handful of warm soil with a young seedling",
                ),
            },
        },
        "onde": (
            "on dark slate", "on aged oak wood", "on rough natural linen", "on pale limestone",
            "on a dark walnut table", "on a sage-green ceramic tile", "on a woven straw mat", "on matte charcoal stone",
        ),
        "comp": (
            "close-up on the seam with shallow depth of field", "three-quarter view at eye level",
            "low angle with generous negative space", "soft top-down angle", "wide framing with the object small",
            "a centered, quiet, symmetrical composition",
        ),
        "atmo": (
            "a nearly silent, meditative stillness", "a faint warm haze in the air", "a clean crisp morning clarity",
            "a few dust motes drifting in the light",
        ),
    },

    # ───────────────────────────── FUMAÇA ─────────────────────────────
    "smoke": {
        "conceito": (
            "an ethereal, tactile atmospheric photograph about anxious, racing thoughts loosening and dissolving: "
            "soft volumes of mist, vapor, smoke or other weightless matter are the hero, with convincing fluid "
            "dynamics, delicate translucent edges and slow calm motion frozen mid-flow. The feeling is weight "
            "leaving the chest and air returning, with clean clear space opening above the dissipating shapes"
        ),
        "luz": (
            "backlit by a low warm solar-orange dawn glow that lights the edges of the shapes",
            "side-lit teal light with a thin orange edge",
            "cold navy shadows opening to warm light at the top of the frame",
            "a single beam of golden light slicing through the shapes",
            "soft diffused white morning light with a subtle teal cast",
        ),
        "familias": {
            "incenso_e_vapor": {
                "g": "tensao visto recomeco novo_dia",
                "s": (
                    "a single thread of incense smoke rising straight, then unfurling into a slow spiral",
                    "steam rising from a cup of tea and braiding into two slow ribbons",
                    "the last wisp from a just-extinguished candle drawing a delicate S-curve upward",
                    "warm steam from a ceramic pot of herbal infusion drifting sideways across a beam of light",
                ),
            },
            "nevoa_de_ambiente": {
                "g": "tensao tristeza recomeco novo_dia",
                "s": (
                    "low mist pooling on a sunlit garden path while clear air opens above",
                    "morning fog between tall slender tree trunks, shafts of warm light slicing through",
                    "a hallway filled with soft haze, a warm glow at the far end, the ceiling area clear",
                    "mist gathering at the foot of an old stone wall and thinning toward the top as the sun rises",
                ),
            },
            "tinta_e_leite": {
                "g": "tensao tristeza autoestima",
                "s": (
                    "teal ink blooming in a clear glass of water, tendrils mid-dissolve against a bright background",
                    "a drop of cream swirling into dark tea, spiralling slowly",
                    "petroleum-teal and navy watercolor pigment blooming on wet paper, edges feathering",
                    "a thin ribbon of golden pigment dispersing in still clear water, glowing from within",
                ),
            },
            "po_e_luz": {
                "g": "visto vazio recomeco novo_dia",
                "s": (
                    "dust motes drifting in a single dawn sunbeam crossing a dark room",
                    "a puff of fine white powder lifting off a dark surface, frozen mid-air and backlit",
                    "golden pollen-like particles lifting from a branch and dispersing into the light",
                    "dandelion seeds detaching and dissolving into a soft haze of light",
                ),
            },
            "tecido_leve": {
                "g": "tensao vazio vinculo recomeco",
                "s": (
                    "a sheer white curtain lifted by the breeze, billowing like smoke in front of a bright window",
                    "a long teal silk scarf drifting through the air, its folds like slow vapor",
                    "fine gauze floating upward, translucent layers overlapping against soft dawn light",
                    "a veil of sage-green tulle dissolving into the air at its upper edge",
                ),
            },
            "respiracao": {
                "g": "tensao tristeza vazio autoestima",
                "s": (
                    "warm breath fogging a cold window glass at dawn, a small clear patch where the fog has already cleared",
                    "a soft cloud of breath visible in cold morning air, backlit by the first sun, no face visible",
                    "steam lifting from a bowl of warm soup, calm, wrapping into the light",
                ),
            },
        },
        "onde": (
            "in a calm dark room", "in a quiet room with a large window", "against a soft gradient backdrop",
            "over a wooden floor and a plain wall", "against a deep petroleum-teal wall", "in an empty bright studio with a cool wall",
        ),
        "comp": (
            "seen straight on", "from a slightly low angle", "wide with generous empty space",
            "a closer framing with soft depth", "a tall vertical composition with the shapes rising toward the top",
        ),
        "atmo": (
            "weightless, slow and calm", "the tension easing as the shapes thin out", "quiet and spacious, air returning",
            "delicate and meditative",
        ),
    },

    # ───────────────────────────── PORTAL ─────────────────────────────
    "portal": {
        "conceito": (
            "a threshold photograph about welcome and the courage of a first step (and a first consultation): an "
            "opening, passage or crossing point leads from a quieter, shadowed side toward luminous dawn light. "
            "The viewer feels invited, never pushed. The light beyond is warm and hopeful; the near side is calm, "
            "safe and softly dark. No one is in the frame"
        ),
        "luz": (
            "golden-orange sunrise light flooding in from beyond the opening",
            "long soft rays through slightly dusty air",
            "a gentle haze lit from behind, warm and welcoming",
            "pale pink-gold dawn light spilling across the floor toward the viewer",
            "cool teal shade on the near side contrasting with warm light beyond",
        ),
        "familias": {
            "portas": {
                "g": "recomeco visto novo_dia vinculo",
                "s": (
                    "a wooden door slightly ajar, bright golden dawn spilling through the gap onto a dark floor",
                    "a tall double door half-open onto a sage-green garden",
                    "a weathered blue door open onto a sunlit courtyard",
                    "a glass door with a sheer curtain, light blooming through it",
                    "a heavy arched wooden door open on a path of light across old stone",
                ),
            },
            "janelas_e_aberturas": {
                "g": "visto tristeza vazio recomeco",
                "s": (
                    "a tall window thrown open, the curtain lifting, a luminous sky beyond",
                    "a small round window like a disc of light in a dark wall",
                    "an open wooden shutter revealing a garden at sunrise",
                    "a skylight above a quiet room pouring a column of dawn light onto the floor",
                ),
            },
            "arcos_naturais": {
                "g": "recomeco autoestima novo_dia",
                "s": (
                    "a tunnel of arching green branches opening onto a bright clearing",
                    "an arch of climbing plants framing a stone path toward sunrise",
                    "a natural gap between two large leafy shrubs revealing golden light",
                    "bamboo stalks parting into a bright corridor",
                ),
            },
            "limiares_urbanos": {
                "g": "recomeco tristeza vazio tensao",
                "s": (
                    "an open iron gate in an old wall onto a street bathed in dawn",
                    "a long corridor ending in a doorway full of light",
                    "a stairwell landing with the last door open onto daylight",
                    "a covered passage emerging from shade into a sunlit square",
                ),
            },
            "veus_e_cortinas": {
                "g": "tensao visto vinculo recomeco",
                "s": (
                    "heavy curtains parted in the middle revealing bright dawn",
                    "a shoji-style sliding paper screen half open onto a garden",
                    "a linen drape swept aside by the breeze revealing a luminous terrace",
                ),
            },
            "consultorio_acolhedor": {
                "g": "visto vinculo recomeco novo_dia",
                "s": (
                    "the door of a calm consulting room slightly ajar, a warm lamp and a teacup glimpsed inside, soft welcoming light",
                    "a welcome mat and a small plant before an open door with warm light inside",
                    "a small bench and a plant beside a half-open door leading to a softly lit room",
                ),
            },
        },
        "onde": (
            "seen from a quiet dark living room", "seen from a simple warm hallway", "seen from a cool shaded stone corridor",
            "seen from a cozy room with a rug", "seen from a stairwell landing", "seen from a softly dark interior with wooden floor",
        ),
        "fora": (
            "a sunrise garden with sage plants", "a soft pastel sunrise sky above green hills", "a stone path across dewy grass",
            "tall plants glowing in backlight", "a warm golden haze with soft shapes of trees", "a quiet courtyard with a small tree",
        ),
        "comp": (
            "seen straight on", "from a low angle", "from a gentle diagonal", "a wide shot with the ceiling visible",
            "a tight framing where the opening fills the middle third",
        ),
        "atmo": (
            "calm, safe and inviting", "a hushed, expectant quiet", "warm light against cool shade", "gentle morning stillness",
        ),
    },

    # ───────────────────────────── GELO ─────────────────────────────
    "ice": {
        "conceito": (
            "a photograph about frozen, numbed emotions beginning to thaw (grief, depression, emotional shutdown). "
            "The sense of cold, stillness and suspended feeling is expressed through frost, crystal, condensation, "
            "glass, cold-toned materials or ice, and the first warmth of dawn light is already changing it. "
            "Transformation from rigid to fluid is the story, not any single object. A plain ice cube is NOT "
            "required and is avoided unless named in the subject"
        ),
        "luz": (
            "first warm solar-orange light refracting through the cold material",
            "soft golden backlight glowing from inside the frozen material",
            "cool teal light with one warm point of orange",
            "low sunrise raking across the frost so every crystal sparkles",
            "pale diffused winter light with a warm halo at one edge",
        ),
        "familias": {
            "vidro_e_condensacao": {
                "g": "tristeza vazio tensao visto recomeco",
                "s": (
                    "a cold window pane fogged and frosted, with a hand-sized clear patch where warm dawn light has melted through",
                    "a glass of cold water with condensation beading and sliding down, one droplet catching a warm spark of light",
                    "a fogged mirror with one wiped arc reflecting only a soft warm glow",
                    "a frost-etched glass pane with fern-like crystal patterns, thawing at the edges where sunrise touches it",
                ),
            },
            "geada_botanica": {
                "g": "tristeza recomeco novo_dia autoestima",
                "s": (
                    "a frost-rimmed fern leaf, half of it already glistening and green where the first sun has reached it",
                    "a spiderweb furred with frost, each thread a line of tiny crystals, a warm glow behind",
                    "blades of frosted grass with one backlit blade releasing a bead of meltwater",
                    "a rosebud under a fine skin of frost, one petal edge blushing warm",
                    "a bare branch tip crusted with hoarfrost, a single swelling green bud beneath",
                ),
            },
            "gelo_como_lente": {
                "g": "visto recomeco novo_dia autoestima",
                "s": (
                    "a clear ice sphere acting as a lens, holding a tiny inverted sunrise inside it",
                    "a frozen flower suspended inside a block of clear ice, warm light glowing from behind",
                    "a thin sheet of ice with a web of cracks letting golden light pour through the fractures",
                    "a slab of ice with a trapped leaf inside, its edges softening into light",
                ),
            },
            "cristal_e_mineral": {
                "g": "vazio tristeza tensao autoestima",
                "s": (
                    "a glacial-blue selenite or quartz cluster with a warm ember of light deep inside",
                    "a geode cut open with icy teal crystals, one facet catching a golden reflection",
                    "fine salt crystals on dark stone, glittering cold, with a single warm highlight",
                    "a smooth blue-white marble sphere veined like ice, a thin gold vein running through it",
                ),
            },
            "neve_e_frio_suave": {
                "g": "tristeza vazio recomeco novo_dia",
                "s": (
                    "fresh powdery snow on a wooden doorstep, first sun sparkling across it, one line of small footprints leading toward the light",
                    "snow sliding off a branch in a puff of crystals backlit by sunrise",
                    "a cold-blue room corner where a single warm sun patch lies on the floor and frost clings to the window",
                    "a warm knitted scarf draped over a frosty fence post with a golden glow behind",
                ),
            },
            "derretimento": {
                "g": "recomeco tristeza novo_dia tensao",
                "s": (
                    "a long icicle releasing a swelling drop that holds a miniature of the dawn inside it",
                    "a thin film of ice on a shallow clay dish breaking into a mosaic as warm light reaches it",
                    "frost crystals on a metal rail dissolving into beads along a line of sunlight",
                    "a droplet falling from a melting edge, frozen mid-air in a spray of tiny points of light",
                ),
            },
        },
        "onde": (
            "on a dark wooden surface", "on a slate tile", "on a windowsill", "on a smooth stone",
            "against a deep navy backdrop", "against a soft teal bokeh", "on a pale linen cloth",
        ),
        "comp": (
            "tabletop scale, macro-like", "eye level with shallow depth of field", "slightly from above",
            "a tight crop with the subject off-center and calm space around it",
        ),
        "atmo": (
            "still, hushed, the first warmth arriving", "cold clarity softening", "quiet, suspended, about to move",
            "crisp winter air with a warm promise",
        ),
    },

    # ───────────────────────────── FLUTUANTE ─────────────────────────────
    "floating": {
        "conceito": (
            "a minimalist, weightless composition with very few symbolic objects (three to five) suspended in "
            "mid-air, each with plenty of room to breathe. The objects are real, tangible and beautifully lit with "
            "believable soft shadows or none, arranged with deliberate rhythm. The emptiness around them is part "
            "of the design and carries the calm. Each object stands for something gentle: care, direction, "
            "opportunity, balance, a first step"
        ),
        "luz": (
            "soft diffused dawn light with gentle shadows",
            "a soft glow from one side with a faint warm rim on each object",
            "even airy studio light with a slight warm horizon glow",
            "a quiet backlight that outlines the objects in light",
        ),
        "familias": {
            "objetos_de_cuidado": {
                "g": "vinculo visto autoestima novo_dia",
                "s": (
                    "a handmade ceramic cup, a sprig of sage and a thin golden thread looping between them",
                    "an open notebook with lifting blank pages, a pencil and a small teacup",
                    "a brass key, a sage leaf and a golden thread: an opportunity about to open",
                    "a seedling lifted in a small clay pot with soil and roots visible, and a golden thread",
                ),
            },
            "natureza_suspensa": {
                "g": "recomeco tristeza novo_dia vazio",
                "s": (
                    "seeds and a single feather drifting upward in a gentle column",
                    "a few sage and teal leaves, a petal and a dandelion seed head arranged along a diagonal",
                    "a branch with a few leaves, a small twist of twigs shaped like a nest and a feather",
                    "dried flower petals rising, with a single bright orange petal as the accent",
                ),
            },
            "papel_e_dobraduras": {
                "g": "recomeco tensao novo_dia visto",
                "s": (
                    "an origami crane and two small paper boats hovering in a loose arc, the paper unmarked",
                    "a paper airplane, a paper lantern and a loose blank page drifting toward the upper right",
                    "a small folded paper house with a warm glow inside and a golden thread attached",
                ),
            },
            "equilibrio_mineral": {
                "g": "tensao autoestima vazio vinculo",
                "s": (
                    "three smooth pebbles balanced in a gentle vertical stack with a feather above them",
                    "a few polished stones of different sizes orbiting an empty center",
                    "a perfect sphere of matte teal ceramic, a smaller sage one and a thin gold ring",
                ),
            },
            "luz_e_fios": {
                "g": "visto vazio vinculo recomeco novo_dia",
                "s": (
                    "three small paper lanterns with a warm glow hovering at different heights",
                    "a loose golden thread drawing a calm spiral in the air with a single bright bead of light on it",
                    "a small glass jar glowing softly, a thin golden thread trailing upward",
                    "a mobile-like arrangement of leaves hanging on invisible lines, catching light",
                ),
            },
            "direcao_e_primeiro_passo": {
                "g": "recomeco novo_dia autoestima",
                "s": (
                    "an antique brass compass, a leaf and a golden thread, the needle pointing toward the light",
                    "a small wooden miniature door frame, a leaf and a golden thread: a first step",
                ),
            },
        },
        "onde": (
            "a petroleum-teal to navy gradient backdrop", "a sage to soft cream gradient with a warm glow",
            "a deep navy backdrop with a subtle warm horizon glow", "a petroleum-teal backdrop with a soft bloom of light",
            "a pale warm-white seamless backdrop with a faint teal floor shadow",
        ),
        "comp": (
            "arranged in a vertical column", "along a gentle diagonal", "in a loose orbit around an empty center",
            "rising from lower-left toward upper-right", "scattered with deliberate asymmetry and a large empty area",
        ),
        "atmo": (
            "weightless and airy, with lots of empty space", "a quiet, almost silent calm", "gentle, hopeful, light as breath",
        ),
    },

    # ───────────────────────────── MACRO ─────────────────────────────
    "macro": {
        "conceito": (
            "an extreme close-up photograph with a premium, jewel-like finish: razor-thin depth of field, tack-sharp "
            "micro-texture on the focal plane and a creamy out-of-focus background with luminous bokeh. The unseen "
            "small detail of ordinary things made monumental, intimate and precious, about attention, care and "
            "noticing the small. The subject is NEVER assumed to be a dewdrop or a leaf; it is exactly the subject "
            "named below"
        ),
        "luz": (
            "a single point of solar-orange light blooming in creamy bokeh",
            "soft window light grazing the surface so every fiber and grain shows",
            "backlight that makes the subject glow from within",
            "a cool teal ambient with one warm highlight on the focal plane",
            "gentle golden-hour side-light with a tiny specular sparkle",
        ),
        "familias": {
            "fios_e_tecidos": {
                "g": "tensao vinculo tristeza recomeco",
                "s": (
                    "woven natural linen threads at extreme magnification, one single gold thread running through the weave",
                    "a knitted wool stitch loop with a loose strand being drawn back into the pattern",
                    "a raw silk fold in petroleum teal, its fibers glowing where the light grazes",
                    "a hand-embroidered golden stitch pulling two edges of cloth together",
                    "a frayed rope fibre bundle whose strands are being re-twisted",
                ),
            },
            "mineral_e_cristal": {
                "g": "autoestima visto tristeza vazio",
                "s": (
                    "a clear quartz crystal point with an internal glow and tiny rainbow inclusions",
                    "the surface of a river pebble with a fine vein of gold running through its grain",
                    "grains of sand magnified into small translucent gems, one lit warm orange",
                    "a slice of agate in teal and sage bands with light passing through it",
                ),
            },
            "botanico": {
                "g": "recomeco novo_dia autoestima tristeza",
                "s": (
                    "a seed pod splitting open to release a fine white thread of seed fluff",
                    "a fern fiddlehead mid-unfurl, the spiral perfectly sharp",
                    "the stamens of a flower dusted with golden pollen",
                    "a dandelion seed head with one seed lifting off, the others softly blurred",
                    "tree bark with deep furrows and a tiny green shoot emerging from a crack",
                    "a bud with its outer scales parting to show new green",
                    "moss capsules on slender stalks, backlit",
                ),
            },
            "objetos_de_cuidado": {
                "g": "visto vinculo autoestima novo_dia vazio",
                "s": (
                    "the nib of a fountain pen resting on blank cream paper, a bead of ink about to touch down",
                    "an old brass key entering a keyhole, the metal teeth and a first thread of warm light through the hole",
                    "the edge of a notebook with pages fanning, the paper fibres lit by sunrise",
                    "the wick and flame of a small candle, the wax rim translucent",
                    "a loose tea leaf unfurling at the surface of warm tea",
                    "tiny brass clock gears meshing, the metal catching the light",
                ),
            },
            "luz_e_optica": {
                "g": "visto novo_dia recomeco autoestima",
                "s": (
                    "a crystal prism splitting a dawn ray into a soft spectrum across a linen surface",
                    "a glass bead holding an upside-down miniature window of sunrise",
                    "soft caustic light patterns dancing on matte teal ceramic",
                    "a soap bubble with slow-moving iridescent colours reflecting a window",
                    "string lights turned into creamy bokeh discs with one bulb in sharp focus",
                ),
            },
            "vida_minuscula": {
                "g": "recomeco autoestima vinculo novo_dia visto",
                "s": (
                    "the scales of a butterfly wing in jewel-like teal and gold, the micro-pattern sharp",
                    "a feather's barbs interlocking like a zipper, one small gap being repaired",
                    "the spiral of a small snail shell, backlit and glowing amber",
                    "a honeybee's fuzzy back dusted with pollen on a flower",
                ),
            },
        },
        "onde": (
            "creamy teal bokeh with a single orange light point", "warm golden bokeh with cool navy edges",
            "sage-green bokeh with white haze highlights", "a deep navy background with scattered soft light discs",
            "a pale cream blur with a faint teal edge", "a dark petroleum background with one far warm glow",
        ),
        "comp": (
            "razor-thin depth of field at eye level with the subject", "slightly from above",
            "from a low angle, backlit", "a diagonal composition with the focal point on a third",
            "a tight crop with the subject off-center and calm space around it",
        ),
        "atmo": (
            "intimate, precious and quiet", "luminous and delicate", "serene attention to something very small",
        ),
    },

    # ───────────────────────────── MUSEU ─────────────────────────────
    "museum": {
        "conceito": (
            "a quiet gallery photograph in which one small symbolic thing is presented like a work of art, giving "
            "dignity to a personal story: gallery-grade lighting, generous empty space, perfect restraint and "
            "silence. The viewer feels that what is displayed deserves to be looked at and respected. No visitors, "
            "no labels with readable text"
        ),
        "luz": (
            "a single soft museum spotlight from above",
            "a skylight beam falling softly on the piece",
            "a side track light grazing the wall texture and the object",
            "dim ambient gallery light with a precise warm pool of light on the subject",
        ),
        "familias": {
            "objeto_em_plinto": {
                "g": "autoestima tristeza visto recomeco novo_dia",
                "s": (
                    "a mended ceramic bowl with gold seams on a low plinth",
                    "a smooth sphere of polished stone on a plinth",
                    "a single hand-thrown vase leaning slightly, glaze crackled, on a plinth",
                    "a worn brass key resting on a pale stone plinth",
                ),
            },
            "moldura_e_vazio": {
                "g": "vazio visto autoestima recomeco",
                "s": (
                    "an empty gilded frame hanging alone on the wall, the wall inside the frame subtly luminous",
                    "a blank canvas leaning against the wall, lit as if it were a masterpiece",
                    "a large empty frame with a dawn-coloured gradient behind it, as if the light were the painting",
                    "a small framed piece of plain linen with a single gold stitch",
                ),
            },
            "instalacao_de_luz": {
                "g": "novo_dia visto recomeco tensao",
                "s": (
                    "a window-shaped patch of dawn light projected on the gallery wall, treated as the artwork itself",
                    "the long soft shadow of a plant cast on the wall by a spotlight, the shadow more beautiful than the plant",
                    "a beam of warm light cutting a rectangle across the floor of an empty gallery",
                ),
            },
            "vitrine_e_memoria": {
                "g": "visto vinculo tristeza vazio",
                "s": (
                    "a small glass vitrine holding a tangle of golden thread slowly unknotting",
                    "a glass dome over a single seedling in a tiny pot of soil",
                    "a small display case with one worn teacup and its saucer, lit softly",
                    "a glass bell jar containing a feather and a small stone",
                ),
            },
            "escultura_abstrata": {
                "g": "tensao autoestima recomeco vinculo",
                "s": (
                    "a polished brass wire sculpture that twists and then gradually untwists into one smooth line",
                    "nested ceramic bowls in teal tones, each mended in gold, arranged as a sculpture",
                    "a curved white marble form with a thin gold vein, resting on a plinth",
                    "two smooth stones joined by a golden thread, displayed as an intimate sculpture",
                ),
            },
            "natureza_como_obra": {
                "g": "recomeco novo_dia tristeza autoestima",
                "s": (
                    "a single branch with one new leaf in a glass cylinder on a plinth",
                    "a cluster of sage leaves pressed behind glass like a botanical plate",
                    "a young plant in a mended pot under a soft museum spotlight",
                ),
            },
        },
        "onde": (
            "a deep navy wall", "a petroleum-teal wall", "a soft sage wall with a warm spotlight",
            "a warm off-white wall with a dark polished floor", "a limewashed warm-grey plaster wall",
            "a dark charcoal-blue wall with a pale oak floor",
        ),
        "comp": (
            "centered and symmetrical with a lot of empty wall", "the piece low in the frame with tall empty wall above",
            "a three-quarter angle with the wall receding", "a close, intimate crop on the piece",
        ),
        "atmo": (
            "silent, refined and reverent", "a hushed gallery stillness", "warm dignity, nothing extra in the room",
        ),
    },
}


def _proxima_familia(estilo, grupo):
    """Rodízio de famílias; prefere (sem quebrar o rodízio) as que combinam com o grupo psicológico do tema."""
    fams = ESTILOS_V71[estilo]["familias"]
    nomes = list(fams.keys())
    chave = (estilo, "_familia")
    fila = _FILAS.get(chave)
    if not fila:
        fila = list(range(len(nomes)))
        random.shuffle(fila)
        if len(fila) > 1 and _ULTIMO.get(chave) == fila[-1]:
            fila[0], fila[-1] = fila[-1], fila[0]
        _FILAS[chave] = fila
    escolhida = None
    for pos in range(len(fila) - 1, -1, -1):
        if grupo in fams[nomes[fila[pos]]]["g"].split():
            escolhida = fila.pop(pos)
            break
    if escolhida is None:
        escolhida = fila.pop()
    _ULTIMO[chave] = escolhida
    return nomes[escolhida]


def montar(estilo, grupo, leitura, seed):
    """Retorna (cena_texto, luz_texto, enriquecimento_texto) para o prompt do estilo."""
    d = ESTILOS_V71[estilo]
    fam = _proxima_familia(estilo, grupo)
    sujeitos = d["familias"][fam]["s"]
    sujeito = sujeitos[_baralho((estilo, fam), len(sujeitos))]
    luz = d["luz"][_baralho((estilo, "luz"), len(d["luz"]))]
    cor = _COR[_baralho((estilo, "cor"), len(_COR))]

    partes = [
        f"MAIN SUBJECT (render exactly this; do NOT replace it with the most obvious cliché of the style): {sujeito}."
    ]
    for eixo, rotulo in _ROTULOS:
        banco = d.get(eixo)
        if banco:
            partes.append(f"{rotulo}: {banco[_baralho((estilo, eixo), len(banco))]}.")
    partes.append(f"Color story: {cor}.")
    partes.append(f"Emotional reading of the image: {leitura}.")
    partes.append(_REGRA_GERAL)
    partes.append(
        f"Make this image clearly different from other generations of the same style (variation {int(seed) % 997})."
    )
    print(f"[v71] estilo={estilo} grupo={grupo} familia={fam}")
    return d["conceito"], luz, " ".join(partes)
