try:
    from fonttools import ttLib
except ImportError:
    import subprocess, sys
    subprocess.check_call([sys.executable, "-m", "pip", "install", "fonttools"])
    from fonttools import ttLib

font = ttLib.TTFont("fonts/AGILERA.OTF")
gsub = font["GSUB"].table
cmap = font.getBestCmap() or {}
rev_cmap = {v: k for k, v in cmap.items()}

print("=== LIGATURAS (liga) ===")
for feat in gsub.FeatureList.FeatureRecord:
    if feat.FeatureTag != "liga":
        continue
    for idx in feat.Feature.LookupListIndex:
        lk = gsub.LookupList.Lookup[idx]
        if lk.LookupType != 4:
            continue
        for sub in lk.SubTable:
            for first_g, ligs in sub.ligatures.items():
                for lig in ligs:
                    seq = [first_g] + list(lig.Component)
                    chars = ""
                    ok = True
                    for g in seq:
                        if g in rev_cmap:
                            chars += chr(rev_cmap[g])
                        else:
                            chars += f"[{g}]"
                            ok = False
                    print(f"  '{chars}' -> {lig.LigGlyph}" + ("" if ok else "  (glifo sem unicode)"))

print()
print("=== ALTERNATES (aalt) ===")
count = 0
for feat in gsub.FeatureList.FeatureRecord:
    if feat.FeatureTag != "aalt":
        continue
    for idx in feat.Feature.LookupListIndex:
        lk = gsub.LookupList.Lookup[idx]
        if lk.LookupType == 1:
            for sub in lk.SubTable:
                for g, alt in sub.mapping.items():
                    ch = chr(rev_cmap[g]) if g in rev_cmap else f"[{g}]"
                    print(f"  '{ch}' ({g}) -> {alt}")
                    count += 1
        elif lk.LookupType == 3:
            for sub in lk.SubTable:
                for g, alts in sub.alternates.items():
                    ch = chr(rev_cmap[g]) if g in rev_cmap else f"[{g}]"
                    print(f"  '{ch}' ({g}) -> {alts}")
                    count += 1
print(f"Total alternates: {count}")
