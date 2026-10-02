#!/usr/bin/env python3
"""Hafta 1 — IFC dosyasını açmak, hiyerarşiyi okumak, mahal listesi çıkarmak.
  python lab/hafta1.py → cikti/HIYERARSI.txt + cikti/MAHAL-LISTESI.csv (+ OLCUMLER.json 'hafta1')"""
import csv
import ifcopenshell, ifcopenshell.geom, ifcopenshell.util.shape as us, ifcopenshell.util.element as ue
import ifcopenshell.util.unit as uu
from ortak import CIKTI, olcum_yaz

f = ifcopenshell.open(str(CIKTI / "OFIS-KAT1.ifc"))

# 1.2 — hiyerarşi: proje > arsa > bina > kat > elemanlar
satirlar = [f"şema: {f.schema} · uzunluk birimi: {uu.get_project_unit(f, 'LENGTHUNIT').Name}"]
def gez(e, d=0):
    ad = e.Name or ""
    uzun = f" — {e.LongName}" if getattr(e, "LongName", None) else ""
    satirlar.append("  " * d + f"{e.is_a()} {ad}{uzun}")
    for rel in getattr(e, "IsDecomposedBy", []):
        for alt in rel.RelatedObjects:
            gez(alt, d + 1)
    for rel in getattr(e, "ContainsElements", []):
        for alt in rel.RelatedElements:
            satirlar.append("  " * (d + 1) + f"{alt.is_a()} {alt.Name}")
gez(f.by_type("IfcProject")[0])
(CIKTI / "HIYERARSI.txt").write_text("\n".join(satirlar) + "\n")
print("\n".join(satirlar))

# 1.3 — mahal listesi: taban alanı ve hacim geometriden hesaplanır
ayar = ifcopenshell.geom.settings()
ayar.set("use-world-coords", True)
liste = []
for m in sorted(f.by_type("IfcSpace"), key=lambda s: s.Name):
    g = ifcopenshell.geom.create_shape(ayar, m).geometry
    alan = us.get_footprint_area(g)
    hacim = us.get_volume(g)
    liste.append({"no": m.Name, "ad": m.LongName, "alan_m2": round(alan, 2), "hacim_m3": round(hacim, 2)})
with open(CIKTI / "MAHAL-LISTESI.csv", "w", newline="") as fp:
    w = csv.DictWriter(fp, fieldnames=list(liste[0]), delimiter=";")
    w.writeheader(); w.writerows(liste)
for r in liste:
    print(r)
toplam = round(sum(r["alan_m2"] for r in liste), 2)
print("toplam alan", toplam)
olcum_yaz("hafta1", {"mahal_sayisi": len(liste), "toplam_alan_m2": toplam, "mahaller": liste})
