"""
python-api/estilos_novos_v72.py  —  v72  —  13 estilos visuais NOVOS (mesma identidade AlvoreSer)

Cada estilo tem uma GAMA de possibilidades (famílias de sujeitos + fundo, enquadramento e atmosfera) que roda em
rodízio via estilos_prompts_v71.montar(); nenhum estilo fica preso a um único objeto.

Estilos: sprout, roots, stone, bluehour, shadow, lamp, thread, mirror, paper, mosaic, shelter, path, watercolor.
Carregado por estilos_card (ESTILOS recebe rotulo/cena/luz a partir daqui) e por estilos_prompts_v71.
Todos: sem pessoas, sem texto legível, paleta marinho/petróleo/sálvia/branco-neve com laranja solar só como luz.
"""

ESTILOS_NOVOS = {
    # ───────────────────────── BROTO ─────────────────────────
    "sprout": {
        "rotulo": "Broto",
        "v71": {
            "conceito": (
                "a photograph about life starting again in unexpected places: a tender new shoot, bud or seedling "
                "pushing into the light after a hard period. Hope is shown through fragility that persists, in "
                "fresh sage and spring greens against calm navy and teal, with a warm dawn glow on the new growth"
            ),
            "luz": (
                "soft golden dawn backlight making the new leaves translucent",
                "gentle side-light with a warm rim on the shoot",
                "diffused morning light with a single warm highlight on the tip of the sprout",
                "low sunrise raking across the surface, long soft shadows",
            ),
            "familias": {
                "broto_improvavel": {"g": "recomeco tristeza novo_dia autoestima", "s": (
                    "a tiny green shoot pushing up through a crack in dark stone",
                    "a seedling rising from a gap between old wooden floorboards",
                    "a sprout emerging from a crack in a plain concrete step, moss around it",
                    "a fern shoot unfurling from a hollow in an old tree stump",
                )},
                "objeto_cotidiano": {"g": "recomeco vazio tristeza vinculo", "s": (
                    "a young seedling growing in a chipped ceramic teacup on a sill",
                    "a sprout rising from soil inside an old open book with blank pages",
                    "a little plant starting in a small glass jar of soil with its roots visible",
                    "a green shoot growing from a mended cracked bowl",
                )},
                "semente_e_terra": {"g": "recomeco novo_dia visto autoestima", "s": (
                    "a seed splitting open in dark warm soil, the first white root and a pale shoot",
                    "a handful-sized mound of rich soil with a single curled shoot, lit from the side",
                    "a row of tiny seedlings in a wooden tray, one slightly taller catching the light",
                )},
                "estufa_e_janela": {"g": "recomeco novo_dia vazio visto", "s": (
                    "seedlings in small clay pots on a windowsill, bathed in sunrise",
                    "a greenhouse bench with trays of new sprouts, glass roof glowing with dawn",
                    "a single potted sprout leaning toward a bright window",
                )},
                "folha_nova": {"g": "recomeco autoestima novo_dia tristeza", "s": (
                    "a new leaf unrolling at the end of a branch, still curled and glistening",
                    "a bulb with a pale green spear breaking through the top",
                    "a bud on a bare branch, scales parting to show a fresh green tip",
                    "a young vine tendril curling toward a bright point of light",
                )},
            },
            "onde": ("on dark slate", "on weathered wood", "on dark rich soil", "on pale stone", "against a soft teal blur", "on a linen cloth"),
            "comp": ("close-up with razor-thin depth of field", "low angle from soil level looking up", "three-quarter view with calm space around", "soft top-down angle"),
            "atmo": ("tender, quiet and hopeful", "fresh morning air, dew in the air", "still, delicate, about to grow"),
        },
    },
    # ───────────────────────── RAÍZES ─────────────────────────
    "roots": {
        "rotulo": "Raízes",
        "v71": {
            "conceito": (
                "a photograph about origin, belonging, family history and what holds us up: roots, trunks and rings "
                "shown as deep, patient strength. Earthy textures in the clinic palette, lit with a warm hopeful "
                "glow so that depth feels safe, never heavy or gloomy"
            ),
            "luz": (
                "warm low sunrise backlight through the trunk and branches",
                "soft side-light that reveals every ridge and grain",
                "diffused misty morning light with a warm edge",
                "a single shaft of dawn light falling on the roots",
            ),
            "familias": {
                "raizes_entrelacadas": {"g": "vinculo visto tristeza autoestima", "s": (
                    "thick tree roots intertwined over a mossy bank, a thin ray of light between them",
                    "roots of two trees growing together into one braid at the base",
                    "roots gripping a mossy stone wall, fine hair-roots catching light",
                    "an exposed root arch forming a small natural doorway at the foot of a tree",
                )},
                "aneis_de_tronco": {"g": "visto tristeza recomeco autoestima", "s": (
                    "the cut face of a trunk with its growth rings, one ring glowing warm gold",
                    "a slice of tree trunk with a hairline crack mended by a gold line",
                    "stacked log ends in warm morning light, rings like a map of years",
                )},
                "arvore_em_contraluz": {"g": "novo_dia vazio recomeco autoestima", "s": (
                    "a single large tree silhouetted against a dawn gradient of teal and orange",
                    "an old tree with a wide crown, light breaking through its branches in rays",
                    "a tree-lined path of trunks in mist with warm backlight",
                )},
                "raiz_e_pedra": {"g": "autoestima recomeco tensao tristeza", "s": (
                    "a root splitting a large boulder and holding it in place, green moss on both",
                    "a young tree growing from the top of a rock, roots hugging down its sides",
                )},
                "raizes_visiveis": {"g": "vinculo visto novo_dia recomeco", "s": (
                    "a plant in a clear glass vase with long white roots visible in clean water, dawn behind",
                    "a bulb with fine roots reaching down, resting in a glass jar on a windowsill",
                    "a sprouted sweet potato or onion with delicate roots in a transparent jar",
                )},
            },
            "onde": ("in a misty forest floor", "against dark earth", "on a mossy bank", "against a soft sage blur", "on aged wood"),
            "comp": ("low angle at ground level", "close crop on texture with soft depth", "wide with the subject small and calm space above", "centered, symmetrical and still"),
            "atmo": ("grounded, patient and safe", "quiet strength", "earthy calm with a hopeful glow"),
        },
    },
    # ───────────────────────── PEDRA ─────────────────────────
    "stone": {
        "rotulo": "Pedra",
        "v71": {
            "conceito": (
                "a photograph about grounding, stability and anchoring when anxiety or panic rises: stones, sand and "
                "rock shown as calm, steady, trustworthy forms. Matte textures and balanced composition in the clinic "
                "palette, a warm dawn touch on the surfaces so stillness feels alive, not cold"
            ),
            "luz": (
                "soft warm side-light that makes the stone grain glow",
                "diffused overcast light with a warm point on the top of the stones",
                "low sunrise raking across the surface and the sand",
                "gentle backlight with a thin warm rim around the forms",
            ),
            "familias": {
                "pilhas_equilibrio": {"g": "tensao autoestima vazio vinculo", "s": (
                    "a small cairn of smooth stones in careful balance, the top stone catching light",
                    "three stones of decreasing size stacked on a wooden surface",
                    "a stack of flat river stones with a single sage leaf resting on top",
                )},
                "jardim_zen": {"g": "tensao visto tristeza autoestima", "s": (
                    "raked sand in slow concentric circles around a single dark stone",
                    "fine sand with gentle wave lines and two stones placed with space between them",
                    "a shallow tray of raked white sand and one mossy stone, morning light",
                )},
                "seixos_lisos": {"g": "vinculo tristeza visto autoestima", "s": (
                    "a handful of smooth river pebbles in teal-grey tones, one with a thin white line around it",
                    "a single perfectly round stone resting in an open palm-sized wooden dish",
                    "pebbles arranged in a loose spiral on dark slate",
                )},
                "rocha_e_musgo": {"g": "recomeco vazio tristeza novo_dia", "s": (
                    "a large mossy boulder with a small fern growing at its base, soft mist",
                    "an old stone wall covered with moss and lichen in dawn light",
                    "a flat rock warmed by the first sun, a thin curl of mist lifting from it",
                )},
                "pedra_com_calor": {"g": "vinculo visto tensao novo_dia", "s": (
                    "a smooth warm stone beside a steaming cup of tea on dark wood, no hands",
                    "a stone with a soft sunbeam lying across it like a blanket of light",
                )},
            },
            "onde": ("on dark wood", "on pale sand", "on dark slate", "on a linen cloth", "against a soft navy wall", "on a mossy ground"),
            "comp": ("centered and calm", "low angle with the stones monumental", "close crop on texture", "wide with generous negative space"),
            "atmo": ("steady and grounding", "slow, still, safe", "quiet weight made gentle"),
        },
    },
    # ───────────────────────── HORA AZUL ─────────────────────────
    "bluehour": {
        "rotulo": "Hora azul",
        "v71": {
            "conceito": (
                "a photograph of the blue hour turning into dawn, the heart of the clinic identity: the long night "
                "(difficult nights, insomnia, waiting) giving way to the first warm light. A calm deep navy and "
                "petroleum-teal sky or space with a gradient into solar orange at the horizon. No water, no sea, "
                "no tourist landscape; quiet and intimate"
            ),
            "luz": (
                "the last blue light of night blending into a thin line of warm orange at the horizon",
                "teal-navy ambient glow with one warm window light",
                "soft pre-dawn glow with a pale peach band low in the sky",
                "cool blue shadows gradually warming at the edges",
            ),
            "familias": {
                "janela_madrugada": {"g": "tristeza vazio tensao visto", "s": (
                    "a window at pre-dawn seen from a dark room, the sky outside teal fading to orange, a plant on the sill",
                    "sheer curtains glowing faintly blue with a warm line of light at the bottom edge",
                    "a wooden window frame with the first light on the glass, a steaming cup on the sill",
                )},
                "ceu_em_transicao": {"g": "recomeco novo_dia tristeza autoestima", "s": (
                    "an open sky gradient from deep navy to petroleum teal to soft orange, a few thin clouds catching light",
                    "high clouds lit from below in peach and rose against a deep teal sky",
                    "a slim crescent moon fading in a dawn gradient above soft dark treetops",
                )},
                "silhuetas_de_natureza": {"g": "novo_dia recomeco vazio autoestima", "s": (
                    "a bare branch silhouetted against the dawn gradient with a single bird",
                    "tall grass and wildflowers silhouetted against a luminous teal-orange sky",
                    "tree crowns in soft silhouette with mist at their base and a glowing horizon",
                )},
                "luzes_da_noite_que_acaba": {"g": "vazio tristeza visto vinculo", "s": (
                    "a small lamp still on in a window of a distant house as the sky turns light",
                    "out-of-focus rooftops and chimneys in blue haze with a few warm window lights",
                    "a quiet street lamp glowing warm against a blue sky about to become day",
                )},
                "interior_amanhecendo": {"g": "recomeco visto novo_dia vinculo", "s": (
                    "a quiet room in cool blue shadow with a stripe of warm sunrise just reaching the floor",
                    "a bed with crisp linen in blue half-light, the first gold touching the blanket",
                )},
            },
            "onde": ("seen through a window", "from a dark interior", "over a calm open field horizon with no water", "above soft out-of-focus treetops"),
            "comp": ("a wide shot with calm space above", "the horizon low in the frame", "a vertical composition with gradient dominating", "the light source off-center near the lower right"),
            "atmo": ("hushed, expectant, the night ending", "a calm breath before the day", "cool and quiet with a warm promise"),
        },
    },
    # ───────────────────────── SOMBRA E LUZ ─────────────────────────
    "shadow": {
        "rotulo": "Sombra e luz",
        "v71": {
            "conceito": (
                "a photograph where light and shadow are the artwork, about self-knowledge, ambivalence and the parts "
                "of ourselves not yet seen: shadows cast on a wall or surface, shapes revealed by light. Only the "
                "shadows of objects, plants and architecture, never of people. Calm, elegant, in navy, teal and sage "
                "with warm light"
            ),
            "luz": (
                "a low warm sunrise light casting long soft shadows across a wall",
                "a hard-edged but warm window light with crisp shadow shapes",
                "diffused light with soft-edged gentle shadows",
                "a single beam cutting a sharp shape of light across a dark surface",
            ),
            "familias": {
                "sombra_de_folhas": {"g": "visto recomeco autoestima novo_dia", "s": (
                    "leaf and branch shadows moving across a plain pale wall, soft and layered",
                    "the shadow of a potted plant cast large and graceful on a teal wall",
                    "dappled light and leaf shadows over a wooden table with a single cup",
                )},
                "janela_e_esquadria": {"g": "visto vazio tristeza novo_dia", "s": (
                    "the cross-pattern shadow of a window frame stretched across the floor in warm light",
                    "a long rectangle of light from a window falling across a dark wooden floor",
                    "the shadow of window bars and curtain folds on a wall at sunrise",
                )},
                "renda_e_tecido": {"g": "vinculo tensao tristeza visto", "s": (
                    "lace-curtain shadow patterns delicately printed across a wall and a table",
                    "sheer curtain shadows rippling in soft light",
                    "the woven pattern shadow of a basket thrown on a wall",
                )},
                "objeto_e_sombra": {"g": "visto autoestima vazio recomeco", "s": (
                    "a simple ceramic cup whose long shadow stretches far across a table, more beautiful than the cup",
                    "a single flower in a vase with its shadow on the wall behind, doubled in light",
                    "a small sphere casting an elongated shadow on a smooth surface",
                )},
                "arquitetura_e_luz": {"g": "tensao autoestima recomeco novo_dia", "s": (
                    "a staircase with bands of light and shadow, empty and quiet",
                    "a plain archway with a bright shaft of dawn light on the floor",
                    "a wall with a rhythm of vertical light stripes from shutters",
                )},
                "meia_luz": {"g": "tensao vinculo visto tristeza", "s": (
                    "an object half in light and half in shadow, the boundary soft and exact",
                    "a smooth white vase split by a clean line of light and shade",
                )},
            },
            "onde": ("on a plain pale wall", "on a deep teal wall", "on warm wooden floor", "on a limewashed plaster surface", "on dark slate"),
            "comp": ("minimal with large empty surface", "close crop of the pattern", "diagonal composition with the light band crossing", "centered and quiet"),
            "atmo": ("quiet, poetic, still", "elegant stillness with moving light", "gentle contrast, nothing harsh"),
        },
    },
    # ───────────────────────── ABRIGO DE LUZ ─────────────────────────
    "lamp": {
        "rotulo": "Abrigo de luz",
        "v71": {
            "conceito": (
                "a photograph of a small, warm light holding the dark at bay, about comfort, grief and quiet company: "
                "a lamp, candle or lit window as shelter. The surroundings are soft navy and teal dusk or pre-dawn; "
                "the light is gentle, golden and never harsh. Intimate, still, nobody in frame"
            ),
            "luz": (
                "a small warm glow as the main light source with a soft falloff into navy shadow",
                "golden lamplight pooling on a wooden surface, cool teal ambience around",
                "candle-warm light with a delicate halo and soft bokeh",
                "the first dawn light mixing with the glow of a small lamp",
            ),
            "familias": {
                "vela_e_lamparina": {"g": "tristeza vazio vinculo visto", "s": (
                    "a single candle in a simple ceramic holder, its flame steady, a soft halo around it",
                    "an oil lamp with a small flame on a dark wooden table beside a sprig of sage",
                    "three small candles at different heights, their glows overlapping gently",
                )},
                "luminaria_de_mesa": {"g": "visto vinculo recomeco autoestima", "s": (
                    "a small table lamp with a linen shade glowing warm in a dark room, a cup of tea beside it",
                    "a vintage brass desk lamp lighting an open empty notebook",
                    "a bedside lamp casting a warm circle on folded linen, the rest in blue shadow",
                )},
                "lanterna": {"g": "recomeco tensao vazio novo_dia", "s": (
                    "a small lantern with a warm light sitting on a stone step in blue dusk",
                    "a paper lantern glowing softly on a dark wooden surface",
                    "a glass lantern with a flame hanging from a branch, mist around",
                )},
                "janela_acesa": {"g": "vinculo visto tristeza vazio", "s": (
                    "a single lit window of a small house in a blue twilight landscape of soft shapes",
                    "a warm lit window seen through a gap in dark leaves",
                    "a cottage window glowing amber in the pre-dawn blue with a plant on the sill",
                )},
                "luzes_pequenas": {"g": "vinculo novo_dia visto recomeco", "s": (
                    "a string of small warm lights draped on a branch, creamy bokeh",
                    "fairy lights in a glass jar glowing on a windowsill",
                )},
            },
            "onde": ("on dark wood", "on a windowsill", "on stone", "on a linen cloth in a dim room", "against a deep teal wall"),
            "comp": ("close and intimate", "the light low in the frame with soft darkness above", "centered, quiet", "a wide dim scene with a tiny glow"),
            "atmo": ("warm, sheltering, silent", "a gentle vigil, nothing alone", "soft dusk comfort"),
        },
    },
    # ───────────────────────── FIO E TECIDO ─────────────────────────
    "thread": {
        "rotulo": "Fio e tecido",
        "v71": {
            "conceito": (
                "a photograph about knots loosening, bonds and weaving a life: thread, yarn, cloth and the craft of "
                "weaving shown as emotion made tangible, with golden threads as the accent. Tactile, soft, "
                "premium textile photography in the clinic palette; anxiety untangling, bonds being woven"
            ),
            "luz": (
                "soft window light grazing the fibers so every strand shows",
                "warm backlight making loose fibers glow",
                "diffused morning light with a gentle warm highlight on gold thread",
                "side-light with a delicate shadow between the threads",
            ),
            "familias": {
                "novelo_e_nos": {"g": "tensao vinculo tristeza recomeco", "s": (
                    "a teal ball of yarn with a loose end unraveling into a long calm line",
                    "a tangled skein of navy and sage yarn with one section already smoothed out",
                    "a knot of thread half-undone, the ends relaxing in soft light",
                )},
                "teia_e_rede": {"g": "vinculo visto tensao vazio", "s": (
                    "a delicate spiderweb beaded with light between two branches",
                    "a fishing-net-like macramé hanging, knots in warm light",
                )},
                "tear_e_tecelagem": {"g": "vinculo recomeco autoestima novo_dia", "s": (
                    "a small wooden loom with partly woven teal cloth and a golden weft thread",
                    "warp threads stretched taut with a shuttle resting beside them",
                    "a hand-woven textile in sage and navy with a single gold stripe",
                )},
                "bordado_e_costura": {"g": "tristeza recomeco vinculo autoestima", "s": (
                    "an embroidery hoop with a half-finished floral pattern in sage and gold thread, needle resting",
                    "a spool of golden thread and a needle on dark linen",
                    "a fabric edge stitched in gold, the stitches small and regular",
                )},
                "fios_pelo_ar": {"g": "novo_dia visto vazio tensao", "s": (
                    "a long golden thread drawing a slow curve through the air against a soft backdrop",
                    "several thin threads of teal and gold floating and crossing like light",
                )},
            },
            "onde": ("on dark linen", "on aged wood", "against a deep teal blur", "on a pale cloth", "against a soft sage backdrop"),
            "comp": ("close-up on the texture with shallow depth", "a loose diagonal flow of thread across the frame", "top-down with the thread forming a calm curve", "off-center with open space"),
            "atmo": ("tactile and quiet", "patient craft, calm hands-free stillness", "soft, slow, careful"),
        },
    },
    # ───────────────────────── ESPELHO ─────────────────────────
    "mirror": {
        "rotulo": "Espelho",
        "v71": {
            "conceito": (
                "a photograph about self-image, being seen and identity: mirrors and polished or reflective surfaces "
                "that show only light, windows, plants or the sky, never a person or a face. Elegant, restrained, "
                "in navy, teal and sage with a warm dawn reflection"
            ),
            "luz": (
                "dawn light reflected in the surface, a warm glow within the mirror",
                "soft window light with a clean specular highlight",
                "low warm sunrise skimming the polished surface",
                "cool teal ambient with one warm reflection",
            ),
            "familias": {
                "espelho_redondo": {"g": "visto autoestima novo_dia recomeco", "s": (
                    "a round mirror leaning on a wall, reflecting only a window full of sunrise and a plant",
                    "a small hand mirror lying on linen, its glass holding a pale golden sky",
                    "a round mirror hanging on a deep teal wall reflecting a soft warm lamp",
                )},
                "superficie_polida": {"g": "visto autoestima vazio tensao", "s": (
                    "a polished brass bowl reflecting a warm blur of dawn windows",
                    "a smooth steel sphere on a wooden surface reflecting a distorted bright window",
                    "a highly polished dark stone slab with a soft golden reflection of the sky",
                )},
                "vidro_e_reflexo": {"g": "tristeza visto vazio recomeco", "s": (
                    "a window pane reflecting the room's soft lamp over a blue dawn landscape outside",
                    "a glass door reflecting a garden and warm light at the same time",
                    "a large pane of glass with the reflection of leaves layered over the view beyond",
                )},
                "agua_em_pequeno": {"g": "tensao vazio visto tristeza", "s": (
                    "a shallow ceramic bowl of still water reflecting the pale dawn sky above",
                    "a single clear drop on a dark surface mirroring a miniature window of light",
                )},
                "espelho_antigo": {"g": "visto vinculo tristeza autoestima", "s": (
                    "an old mirror with a weathered gilded frame reflecting only a warm blur of light",
                    "a convex mirror in a corner reflecting a distorted calm room with no one in it",
                )},
            },
            "onde": ("against a plain wall", "on a wooden surface", "on a linen cloth", "in a quiet dim room", "against a soft sage backdrop"),
            "comp": ("centered and calm", "a three-quarter view with soft depth", "close crop on the reflection", "with generous empty wall around it"),
            "atmo": ("quiet, introspective", "clear, still, honest", "reflective calm with warm light"),
        },
    },
    # ───────────────────────── PAPEL E ESCRITA ─────────────────────────
    "paper": {
        "rotulo": "Papel",
        "v71": {
            "conceito": (
                "a photograph about processing, expression and therapeutic writing: paper, notebooks and the tools of "
                "writing as a quiet space where feelings find form. No legible text, only blank or abstract marks. "
                "Soft, warm, tactile still life in the clinic palette"
            ),
            "luz": (
                "soft morning window light across the paper fibres",
                "warm lamp-like glow with a gentle falloff",
                "diffused daylight with a faint warm edge",
                "low sunrise light creating delicate shadows on the page",
            ),
            "familias": {
                "diario_em_branco": {"g": "recomeco vazio tristeza novo_dia", "s": (
                    "an open blank notebook with a pen lying across it, a cup of tea nearby",
                    "a closed linen-bound journal with a ribbon bookmark and a sage sprig",
                    "an open notebook with just a few soft pencil lines that are not readable",
                )},
                "papel_alisado": {"g": "tensao recomeco autoestima tristeza", "s": (
                    "a crumpled sheet of paper slowly smoothing open, creases catching light",
                    "paper unfolding like a flower, creases still visible",
                    "a flattened sheet with a mended fold line traced in gold",
                )},
                "dobraduras": {"g": "recomeco novo_dia vinculo tensao", "s": (
                    "an origami crane resting on a dark wooden table, light on its folds",
                    "a small paper boat on a wooden surface beside a leaf",
                    "a row of folded paper shapes from simple to refined, unmarked paper",
                )},
                "carta_e_envelope": {"g": "vinculo visto tristeza vazio", "s": (
                    "a plain sealed envelope on a table beside a sprig of sage, unaddressed",
                    "a stack of unmarked cream envelopes tied with a thin golden thread",
                    "a letter paper folded and tucked under a teacup, blank",
                )},
                "livros_e_marcadores": {"g": "visto autoestima novo_dia vinculo", "s": (
                    "a small stack of closed books with a bookmark ribbon and a pen on top",
                    "an open book with soft light across its pages, the text out of focus and unreadable",
                    "pages fanning in the light with a feather-like shadow",
                )},
            },
            "onde": ("on a wooden desk", "on a windowsill", "on dark linen", "on a smooth stone surface", "against a soft teal wall"),
            "comp": ("soft top-down angle", "three-quarter angle with shallow depth", "close crop on the paper texture", "wide with generous empty space"),
            "atmo": ("quiet, thoughtful, unhurried", "calm space to begin", "gentle and private"),
        },
    },
    # ───────────────────────── MOSAICO ─────────────────────────
    "mosaic": {
        "rotulo": "Mosaico",
        "v71": {
            "conceito": (
                "a photograph about integration: parts of oneself rearranging into a whole. Fragments, tiles, "
                "pieces and colored light fitted together with intention. Unlike mending, the idea here is "
                "reorganising, not repairing: teal, navy, sage and warm gold pieces in harmony"
            ),
            "luz": (
                "soft window light with subtle sparkle on the glazed surfaces",
                "warm low light that makes the gold pieces glow",
                "diffused morning light with delicate shadows between the pieces",
                "backlight through colored glass casting soft color",
            ),
            "familias": {
                "azulejos": {"g": "autoestima visto recomeco vinculo", "s": (
                    "a wall of handmade teal, navy and sage tiles with one gold tile among them",
                    "a few ceramic tiles arranged on a table, one set slightly apart as if about to be placed",
                    "a worn tiled floor pattern with warm light crossing it",
                )},
                "quebra_cabeca": {"g": "tensao autoestima recomeco vinculo", "s": (
                    "wooden jigsaw pieces in teal and navy almost complete, one piece still held above the gap",
                    "a few puzzle pieces with a warm golden light passing through the missing space",
                )},
                "vitral_e_luz_colorida": {"g": "novo_dia recomeco visto autoestima", "s": (
                    "soft colored light from a stained-glass window falling on a pale wall in teal, gold and sage",
                    "a small stained-glass panel on a windowsill throwing a mosaic of light onto the wood",
                )},
                "seixos_e_cacos": {"g": "tristeza recomeco vazio vinculo", "s": (
                    "small colored pebbles and sea-glass-like fragments arranged in a loose circle on dark slate",
                    "a hand-laid mosaic of small stones forming a calm pattern, one gold stone at the center",
                )},
                "patchwork": {"g": "vinculo tristeza autoestima recomeco", "s": (
                    "a patchwork quilt of teal, navy, sage and cream squares in soft light, one gold square stitched in",
                    "fabric squares laid out in an arrangement with one gap still waiting",
                )},
            },
            "onde": ("on dark wood", "on a plain pale surface", "on a deep navy surface", "on a linen cloth", "against a soft sage backdrop"),
            "comp": ("top-down with a calm arrangement", "close crop with shallow depth of field", "a diagonal flow of pieces", "centered with empty space around"),
            "atmo": ("ordered, patient, harmonious", "quiet joy of things fitting", "calm and bright"),
        },
    },
    # ───────────────────────── REFÚGIO ─────────────────────────
    "shelter": {
        "rotulo": "Refúgio",
        "v71": {
            "conceito": (
                "a photograph about safety, childhood, rest and self-care: a small, cozy place made for being safe, "
                "lit with warmth. Blankets, soft textures, little roofs and nooks. Nobody in frame. Palette of navy, "
                "teal and sage with a golden warm glow, never gloomy"
            ),
            "luz": (
                "warm golden light spilling from inside the shelter into the soft dusk",
                "soft morning light through a window onto knitted textures",
                "a gentle lamp glow with a cool teal ambience around",
                "diffused dawn light, soft and enveloping",
            ),
            "familias": {
                "cabana_e_casinha": {"g": "vinculo tristeza recomeco vazio", "s": (
                    "a small wooden cabin with one lit window in a soft blue clearing, mist at its feet",
                    "a tiny garden hut with a warm lantern inside and sage plants around",
                    "a treehouse-like little wooden house glowing warmly among dark leaves",
                )},
                "canto_de_leitura": {"g": "visto autoestima tristeza vinculo", "s": (
                    "a cozy reading corner with a knitted blanket, a cushion, a cup of tea and a small lamp, empty",
                    "a window seat with soft cushions and a folded blanket in morning light",
                    "a stack of books and a mug beside a plant on a low shelf, warm light",
                )},
                "tenda_e_forte": {"g": "tensao vinculo tristeza recomeco", "s": (
                    "a small canvas tent lit softly from inside against a deep teal dusk",
                    "a blanket fort draped over chairs, a warm glow spilling from the opening",
                )},
                "varanda_e_cobertor": {"g": "vinculo novo_dia vazio visto", "s": (
                    "a porch with a folded wool blanket on a wooden bench and a steaming cup at dawn",
                    "a hammock with a soft blanket on a quiet veranda in soft morning light",
                )},
                "ninho_e_abrigo": {"g": "recomeco vinculo tristeza novo_dia", "s": (
                    "a bird's nest in a tree fork with soft light, small and secure",
                    "a hollow tree trunk like a tiny doorway with warm light and moss inside",
                )},
            },
            "onde": ("in a quiet garden", "in a dim cozy room", "in a misty clearing", "on a wooden porch", "against a soft sage backdrop"),
            "comp": ("a wide quiet shot with the shelter small", "an intimate close view", "eye level, calm and centered", "a low angle with soft depth"),
            "atmo": ("safe, soft, warm", "a held, unhurried quiet", "childhood-gentle comfort"),
        },
    },
    # ───────────────────────── CAMINHO ─────────────────────────
    "path": {
        "rotulo": "Caminho",
        "v71": {
            "conceito": (
                "a photograph about the therapeutic process as a journey, step by step: a path, stairs or stepping "
                "stones leading toward a gentle light. Direction without hurry; the way is visible but not "
                "forced. Nobody walking, no figures. Calm navy, teal and sage with a warm dawn light ahead"
            ),
            "luz": (
                "warm golden-orange dawn light waiting at the end of the path",
                "long soft rays filtering through trees onto the way",
                "diffused misty light with a warm glow at the far end",
                "low sunrise raking across the steps and stones",
            ),
            "familias": {
                "trilha_de_floresta": {"g": "recomeco novo_dia tristeza autoestima", "s": (
                    "an earthy forest trail curving gently toward a bright clearing, mist and light rays",
                    "a narrow dirt path between tall ferns leading to a golden light",
                    "a path of fallen leaves under tall trees, a luminous gap ahead",
                )},
                "escada_de_pedra": {"g": "recomeco autoestima tensao novo_dia", "s": (
                    "a rustic stone staircase between green plants rising toward soft sunrise light",
                    "a short flight of worn stone steps with moss on the edges and light at the top",
                    "a curved garden staircase with a lantern at the first step",
                )},
                "passos_de_pedra": {"g": "tensao autoestima vazio recomeco", "s": (
                    "round stepping stones set in moss, leading in a gentle curve toward warm light",
                    "flat stones across a pebble garden in a calm line",
                )},
                "ponte_e_travessia": {"g": "recomeco tristeza vazio autoestima", "s": (
                    "a simple wooden footbridge over a misty ravine, light at the far end, no one on it",
                    "a wooden plank bridge among leafy shrubs in soft morning mist",
                )},
                "jardim_e_aleia": {"g": "vinculo visto novo_dia recomeco", "s": (
                    "a garden path lined with low sage plants and a small gate half open at the end",
                    "an avenue of trees forming a green tunnel, warm light at its end",
                    "a gravel path with a soft curve between flowering shrubs at sunrise",
                )},
            },
            "onde": ("in a quiet forest", "in a tended garden", "among tall grass", "in a stone courtyard", "on a hillside with soft mist"),
            "comp": ("the path leading into the frame from the lower left", "a low angle along the path", "a wide shot with calm sky and the path small", "an S-curve composition"),
            "atmo": ("patient, step by step", "quiet and hopeful, no rush", "morning mist with a warm end point"),
        },
    },
    # ───────────────────────── AQUARELA ─────────────────────────
    "watercolor": {
        "rotulo": "Aquarela",
        "v71": {
            "conceito": (
                "an abstract fluid art photograph about emotions that have no name yet: washes, blooms and flows of "
                "pigment in petroleum teal, navy and sage with threads of warm gold and a touch of solar orange. "
                "Entirely non-figurative: no objects, no landscape, no people, no text. Soft edges, translucent "
                "layers and beautiful paper texture; gentle, not chaotic"
            ),
            "luz": (
                "soft even light showing the translucency of the layered pigment",
                "a warm glow from one corner as if light passes through the paper",
                "diffused daylight with a faint sheen on the wet pigment",
                "a gentle luminous bloom at the center of the composition",
            ),
            "familias": {
                "manchas_e_lavados": {"g": "tristeza vazio tensao visto", "s": (
                    "broad translucent washes of teal and navy blending softly on textured cotton paper, a pale light area in the center",
                    "soft overlapping washes in sage and petroleum with a delicate pale gap, edges feathering",
                    "a cloud of navy pigment bleeding into a teal wash with a hint of warm orange at one edge",
                )},
                "flores_de_pigmento": {"g": "recomeco novo_dia autoestima tristeza", "s": (
                    "a bloom of teal pigment opening on wet paper like a flower, fine blooming edges",
                    "droplets of sage and gold pigment bleeding outward on wet paper into small rounded blooms",
                )},
                "ouro_e_aquarela": {"g": "recomeco tristeza autoestima vinculo", "s": (
                    "teal and navy washes crossed by thin lines of gold leaf like mended cracks",
                    "a wash of sage with flecks of gold pigment catching the light",
                )},
                "marmorizacao": {"g": "tensao vazio visto autoestima", "s": (
                    "suminagashi-style marbling in navy, teal and cream, concentric rippling rings",
                    "flowing marbled lines of teal, sage and gold swirling gently across paper",
                )},
                "gradientes_de_alvorada": {"g": "novo_dia recomeco tristeza visto", "s": (
                    "a vertical wash from deep navy at the top through teal to a soft peach-orange glow at the bottom",
                    "a gentle sunrise-like wash with pale cream and soft orange rising from the lower edge of teal paper",
                )},
            },
            "onde": ("on rough cold-press cotton paper", "on smooth hot-press paper with visible pigment pooling", "on handmade paper with fibre flecks", "on a pale warm-white paper"),
            "comp": ("a full-frame abstract composition", "a soft diagonal flow", "an off-center bloom with open space", "a calm layered vertical composition"),
            "atmo": ("fluid, quiet and soft", "emotions without names, gently moving", "luminous and delicate"),
        },
    },
}
