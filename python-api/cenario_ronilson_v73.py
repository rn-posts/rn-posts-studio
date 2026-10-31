"""
python-api/cenario_ronilson_v73.py  —  v73  —  Cenários em ESCALA HUMANA para o "Com Ronilson" + limpeza do piso de estúdio

Problema: nos estilos poéticos o cenário saía como objeto/close (espelho enorme, cama como chão, fundo muito borrado)
e o Ronilson, em pé e nítido, parecia "colado". Agora o cenário é um LUGAR REAL, fotografado na altura dos olhos de
um adulto em pé, com chão firme visível, foco profundo e o elemento do estilo em tamanho real à esquerda, deixando a
direita livre para ele. Cada estilo tem vários ambientes em rodízio (baralho), então não repete e não é literal.

Usado por estilos_card._prompt_cenario_ronilson (flag _CENARIO_HUMANO_V73). Falhou? O fluxo anterior é usado.
"""
import random

import numpy as np

AMBIENTES = {
    # ── os 7 poéticos já existentes ──
    "gold": (
        "a sunlit stone courtyard wall on the left with a long crack repaired in glowing gold leaf running down the plaster, potted sage plants at its foot, flagstone ground",
        "an old wooden workshop door and frame on the left with deep cracks filled with gold, a worn stone doorstep, soft morning light",
        "a quiet ceramics studio: wall shelves on the left holding handmade mended bowls and vases in teal and navy with gold seams, a wooden floor, warm window light",
        "a garden path beside a low old clay wall whose cracked tiles are mended with gold lines, ferns at its base, gravel ground",
        "a mature tree in a quiet park with a split trunk partly filled with gold, soft backlight, packed earth path",
        "a weathered concrete wall and step in an urban courtyard with fissures filled with gold, moss and a small plant, paved ground",
    ),
    "smoke": (
        "a misty garden path at sunrise, low mist rolling over the grass at left, clear air above, tall trees, a dirt path in the foreground",
        "a stone porch at dawn with a thin ribbon of incense smoke rising from a small burner on a ledge at left, wooden floor",
        "a wooden deck at dawn with mist drifting between potted plants on the left and a sheer curtain moving gently",
        "a long hallway with sheer curtains billowing softly along the left wall, light from the window, wooden floor",
        "a forest edge with shafts of warm light through slowly drifting fog, a mossy earth path",
    ),
    "portal": (
        "a tall wooden doorway standing open in an old stone wall on the left of a courtyard, bright dawn light and sage plants beyond, flagstones in front",
        "a garden gate half open in a whitewashed wall, a path of pale stones leading through, sunrise beyond",
        "an arched passage between leafy hedges with a bright golden gap at the end, gravel path",
        "a wide glass door opening onto a terrace at sunrise, wooden floor with soft reflections of light",
        "a bamboo corridor opening into a bright clearing, packed earth path",
    ),
    "ice": (
        "a frosty winter garden at dawn: white frost on grass and shrubs on the left, the first warm sun beginning to melt it, a stone path",
        "a greenhouse with frosted glass panes glowing warm, stone floor, plants at left",
        "a cold blue-lit room with a large frosted window on the left and a patch of warm sun on the wooden floor",
        "a quiet path through bare frosted trees with the first sun warming the frost, no water",
    ),
    "floating": (
        "a bright courtyard path where several paper lanterns and leaves hover in mid-air at different heights in the left half, otherwise calm, flagstone ground",
        "an airy minimalist room with a wooden floor and a large window on the left, a few feathers, seeds and leaves floating in the light",
        "a meadow path at sunrise with dandelion seeds and a few paper cranes drifting upward on the left",
        "an empty gallery-like room with a wooden floor and a few small objects (a cup, a leaf, a key) suspended at eye level on the left",
    ),
    "macro": (
        "a garden path with dew-covered ferns and a glinting spider web in the left foreground, softly blurred trees behind, clear path ground",
        "a mossy stone wall on the left with tiny seedlings growing in its cracks, a path in front, sunrise light",
        "a flower-meadow edge with seed heads in sharp focus on the left, soft background, a mown grass path",
        "a stone terrace with small potted succulents and a trellis of climbing vines on the left, morning light",
    ),
    "museum": (
        "a minimalist art gallery with a pale polished concrete floor and a deep navy wall holding one large empty gilded frame at eye height on the left, soft spotlight",
        "a gallery room with a low stone plinth on the left holding a mended ceramic bowl, a soft sage wall, wooden floor",
        "a quiet museum hall where a skylight casts a window-shaped patch of light on the wall and floor",
        "a gallery wall with large soft abstract teal paintings on the left and a polished floor, nothing else",
    ),
    # ── os 13 novos ──
    "sprout": (
        "a stone courtyard where a young shrub grows from a crack in the pavement at left, sunrise light, flagstones",
        "a greenhouse with rows of seedling trays on benches at left, brick floor, glass roof full of dawn light",
        "a cracked old wall with ferns and young plants sprouting from it on the left, a path in front",
        "a vegetable garden at dawn with young sprouts in neat rows on the left, a soil path",
    ),
    "roots": (
        "a forest path where huge tree roots arch over the ground on the left, moss, soft rays, earthy path",
        "an old giant tree with wide roots in a park, packed earth ground, morning backlight",
        "a mossy stone wall gripped by tree roots on the left, a dirt path",
    ),
    "stone": (
        "a zen-like stone garden with raked pale gravel ground, a few large stones on the left, a low wall, morning light",
        "a hillside path with large mossy boulders at left, soft mist, a rocky earth path",
        "a dry-stone wall in a meadow with a flat stone path at sunrise",
        "a quiet courtyard with a balanced cairn of smooth stones on the left beside a stone wall",
    ),
    "bluehour": (
        "a quiet rooftop terrace at pre-dawn blue hour with a light railing and a softly blurred city of warm window lights, a teal-to-orange sky gradient, wooden deck floor",
        "a calm balcony with plants at left, a deep blue sky turning orange at the horizon, tiled floor",
        "an open field path at blue hour with tree silhouettes and a warm glow at the horizon, no water",
        "a quiet street corner at first light with lampposts still lit and a blue sky, paved sidewalk",
    ),
    "shadow": (
        "a bright plaster wall on the left with long shadows of leaves and window frames across it, wooden floor at dawn",
        "a courtyard wall with dappled leaf shadows and a stone floor crossed by a bar of light",
        "an arcade corridor with arches casting rhythmic bands of light and shadow on floor and wall",
        "a stairwell landing with window bars casting shadow patterns on whitewashed walls, tiled floor",
    ),
    "lamp": (
        "a cozy porch at blue dusk with a warm lantern on a wooden post at left and a wooden floor, soft sage plants",
        "a library nook with a warm floor lamp glowing on the left, bookshelves, wooden floor",
        "a stone garden path at dawn lit by small lanterns along the left side, light mist",
        "a dim studio with one warm window glowing on the left and a small table lamp glowing far in the background",
    ),
    "thread": (
        "a weaving studio with a large wooden loom on the left holding teal woven cloth and golden thread, wooden floor, window light",
        "a garden path with a spiderweb glittering between shrubs on the left and long threads of golden yarn draped from branches",
        "a textile workshop wall on the left with skeins of yarn in teal, sage and navy hanging neatly, wooden floor",
        "a porch with a hanging macramé curtain on the left in soft light, wooden deck",
    ),
    "mirror": (
        "a large round mirror about one metre wide hanging at eye height on a deep teal wall at the left, reflecting only a window with morning light and a plant, wooden floor",
        "a tall standing mirror leaning on a plain wall at the left, reflecting only soft window light and a green plant, wooden floor",
        "a glass-walled room with big windows on the left reflecting the garden, polished floor",
        "an old courtyard with a convex garden mirror on a stone wall at left reflecting only greenery and sky, flagstones",
    ),
    "paper": (
        "a bright study room with a long wooden desk against the left wall holding open blank notebooks, wooden floor, big window",
        "a library aisle with tall shelves on the left, warm lamps, wooden floor",
        "a quiet courtyard with paper cranes hanging from a tree on fine lines at left, stone floor",
        "a calm studio wall on the left with long blank paper scrolls hung from the ceiling, light wooden floor",
    ),
    "mosaic": (
        "a tiled courtyard wall on the left with a large mosaic of teal, navy, sage and gold tiles, a tiled floor, morning light",
        "a stained-glass window on the left casting colored light patches on a wooden floor and plain wall",
        "a garden path of patchwork tiles in teal and cream leading past a mosaic planter, morning light",
        "a small plaza with a mosaic-paved floor in teal, navy and gold tones, soft light",
    ),
    "shelter": (
        "a small wooden cabin at the left edge of a clearing with a warm lit window, a wooden deck in front, soft mist, trees",
        "a cozy porch with a hammock and a knitted blanket on the rail at left, plants, wooden deck, dawn",
        "a garden shed with a warm lantern and climbing plants on the left, gravel path",
        "a quiet veranda with a low wooden bench-free railing, soft cushions stacked in a corner, wooden deck, golden morning light",
    ),
    "path": (
        "a forest trail curving to the left with light at its end, a wide packed-earth ground in the foreground",
        "a garden with a stone staircase rising on the left in the middle ground and a flat stone landing in the foreground",
        "a path of stepping stones in moss leading toward a gate, wide mossy ground",
        "an avenue of trees with a wide gravel path and morning rays",
    ),
    "watercolor": (
        "a bright art studio whose left wall holds huge soft abstract watercolor paintings in teal, navy and sage, a wooden floor",
        "a plaster wall painted with soft washes of teal and gold pigment like a mural, polished concrete floor",
        "a gallery hallway with large translucent watercolor canvases on the left, pale floor",
        "a courtyard wall with abstract color washes in teal and sage at dawn, stone floor",
    ),
}

_fila = {}
_ultimo = {}


def _proximo(estilo):
    n = len(AMBIENTES[estilo])
    fila = _fila.get(estilo)
    if not fila:
        fila = list(range(n))
        random.shuffle(fila)
        if n > 1 and _ultimo.get(estilo) == fila[-1]:
            fila[0], fila[-1] = fila[-1], fila[0]
        _fila[estilo] = fila
    i = fila.pop()
    _ultimo[estilo] = i
    return AMBIENTES[estilo][i]


_CAMERA = (
    "CAMERA: wide-angle 28-35mm lens held at standing eye level (about 1.5 m high) looking straight ahead, vertical 4:5; "
    "the horizon / vanishing line sits about one quarter of the way down from the top of the frame, so the lower 55-65% "
    "of the frame is firm, flat, walkable ground or floor (wood, stone, gravel, tiles, packed earth, a mown path) with "
    "clearly visible texture and believable perspective. The ground is NEVER a bed, bedding, sofa, table or any soft "
    "furnishing. "
    "FOCUS: deep, natural photographic focus: foreground and middle ground are sharp and only the far background falls "
    "gently out of focus; no macro look, no tilt-shift, no heavy blur. "
    "SCALE: every object at real-life size relative to a 1.75 m tall adult who will later stand in the right-hand "
    "foreground: doors about 2 m, mirrors under 1.2 m, normal window heights, natural plants and trees. "
    "COMPOSITION: the main element of the place sits in the LEFT 45% and the middle ground; the RIGHT 45% of the frame "
    "is calm open floor or ground with a plain, softly lit background where the person will stand, with nothing in it. "
    "LIGHT: soft warm morning light from the left or front with gentle shadows falling to the right and slightly toward "
    "the viewer, one consistent direction, mid-to-high key, never gloomy; no sun disc, lamp or glare behind the right "
    "side. "
)

_REGRAS = (
    "No water, sea, lake or wet reflective ground. No chairs, armchairs, sofas or benches in the frame. "
    "The scene is EMPTY of people: no figures, faces, hands, silhouettes, ghostly or blurred human shapes, reflections "
    "of people, statues, mannequins or portraits anywhere, especially not in the right-hand area. "
)


def prompt(estilo, tema_limpo, seed, leitura, tentativa=0):
    """Prompt de cenário em escala humana para o estilo (ver AMBIENTES)."""
    contexto = f' Concept / emotional theme of this post: "{tema_limpo}". ' if tema_limpo else " "
    p = (
        "Photorealistic editorial photograph of an EMPTY real place (no people) for AlvoreSer, a Brazilian psychology "
        "clinic whose identity is dawn, hope, emotional care, healing and transformation."
        f"{contexto}"
        f"PLACE (the idea of the style shown at real, human scale; the emotional meaning comes from light and mood, "
        f"never from literal props): {_proximo(estilo)}. "
        f"{_CAMERA}"
        "Color palette strictly harmonious with clinic identity: deep navy #024059, petroleum teal #1B797D, soft sage "
        "#779993, solar orange #F9AB0B as accent light only, snow white haze #F4F6F8. "
        f"Emotional reading of the image: {leitura}. "
        f"{_REGRAS}"
        f"Make this image clearly different from other generations (variation {int(seed) % 997}). "
        "No text, no letters, no logos, no watermark, no borders, high definition, authentic photographic texture."
    )
    if tentativa > 0:
        p += (" IMPORTANT: the previous attempt contained a person or oversized elements. Make a simple, EMPTY place "
              "only, with real-size objects and no human figure of any kind.")
    return p


def remover_piso_estudio(rgb, a):
    """Remove o 'tablado' cinza do estúdio sob os sapatos do recorte (retângulo claro, liso e opaco na base).
    Heurística conservadora: só apaga blocos neutros, uniformes, largos e encostados na base do corpo."""
    import cv2
    h, w = a.shape
    sol = a > 0.5
    linhas = np.where(sol.any(axis=1))[0]
    if len(linhas) == 0:
        return a
    y1 = int(linhas.max()) + 1
    y0 = max(0, y1 - int(h * 0.11))
    reg = np.asarray(rgb[y0:y1], dtype=np.float32)
    ra = a[y0:y1]
    mx, mn = reg.max(axis=2), reg.min(axis=2)
    sat = (mx - mn) / (mx + 1.0)
    lum = reg.mean(axis=2)
    cand = ((ra > 0.3) & (sat < 0.12) & (lum > 85)).astype(np.uint8)
    cand = cv2.morphologyEx(cand, cv2.MORPH_OPEN, np.ones((3, 3), np.uint8))
    n, lab, st, _ = cv2.connectedComponentsWithStats(cand)
    larg_corpo = max(1, int(sol.any(axis=0).sum()))
    out = a.copy()
    for k in range(1, n):
        x, y, bw, bh, area = (int(v) for v in st[k])
        if bh < 4 or bw < 0.15 * larg_corpo or y + bh < (y1 - y0) - 3:
            continue
        if area / float(bw * bh) < 0.55:
            continue
        comp = lab == k
        if float(lum[comp].std()) >= 14.0:  # textura (tênis claro, meia): mantém
            continue
        comp = cv2.dilate(comp.astype(np.uint8), np.ones((5, 5), np.uint8)) > 0
        out[y0:y1][comp & (ra < 0.999)] = 0.0
        out[y0:y1][comp] = 0.0
        print(f"[ronilson] piso de estudio removido ({bw}x{bh}px)")
    return out
