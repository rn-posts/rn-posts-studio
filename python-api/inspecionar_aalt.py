"""
Inspeciona os glifos alternativos (aalt) da AGILERA.OTF
para maiusculas e minusculas separadamente.
Execute: python inspecionar_aalt.py
"""
from fonttools import ttLib

font = ttLib.TTFont("fonts/AGILERA.OTF")
cmap = font.getBestCmap() or {}
rev_cmap = {v: k for k, v in cmap.items()}

gsub = font["GSUB"].table if "GSUB" in font else None
if not gsub:
    print("Sem GSUB")
    exit()

# Coleta substituicoes aalt (glifos alternativos)
aalt = {}
for feat in gsub.FeatureList.FeatureRecord:
    if feat.FeatureTag != "aalt": continue
    for idx in feat.Feature.LookupListIndex:
        lk = gsub.LookupList.Lookup[idx]
        if lk.LookupType == 1:  # SingleSubst
            for sub in lk.SubTable:
                for g, alt in sub.mapping.items():
                    ch = chr(rev_cmap[g]) if g in rev_cmap else None
                    if ch: aalt[ch] = alt
        elif lk.LookupType == 3:  # AlternateSubst
            for sub in lk.SubTable:
                for g, alts in sub.alternates.items():
                    ch = chr(rev_cmap[g]) if g in rev_cmap else None
                    if ch and alts: aalt[ch] = alts[0]

print(f"\nTotal de glifos com alternativo aalt: {len(aalt)}")
print("\n--- MAIUSCULAS com alternativo ---")
for ch, alt in sorted(aalt.items()):
    if ch.isupper():
        print(f"  '{ch}' (U+{ord(ch):04X}) -> {alt}")

print("\n--- MINUSCULAS com alternativo ---")
for ch, alt in sorted(aalt.items()):
    if ch.islower():
        print(f"  '{ch}' (U+{ord(ch):04X}) -> {alt}")

print("\n--- OUTROS (numeros, simbolos) ---")
for ch, alt in sorted(aalt.items()):
    if not ch.isupper() and not ch.islower():
        print(f"  '{ch}' (U+{ord(ch):04X}) -> {alt}")

# Verifica ligaturas tambem
print("\n--- LIGATURAS (liga) ---")
for feat in gsub.FeatureList.FeatureRecord:
    if feat.FeatureTag != "liga": continue
    for idx in feat.Feature.LookupListIndex:
        lk = gsub.LookupList.Lookup[idx]
        if lk.LookupType != 4: continue
        for sub in lk.SubTable:
            for first_g, ligs in sub.ligatures.items():
                first_ch = chr(rev_cmap[first_g]) if first_g in rev_cmap else "?"
                for lig in ligs:
                    seq = first_ch
                    for g in lig.Component:
                        seq += chr(rev_cmap[g]) if g in rev_cmap else "?"
                    print(f"  '{seq}' -> {lig.LigGlyph}")
