#!/usr/bin/env python3
"""Örnek girdi modeli: OFIS-KAT1.ifc — tek katlı küçük ofis (mimari model; tesisat YOK).
Kursun her haftası bu dosyadan başlar. Ekip tarafından IfcOpenShell API ile üretilir (lisans sorunu yok).
  python lab/bina.py  → lab/cikti/OFIS-KAT1.ifc"""
import ifcopenshell, ifcopenshell.api as api
from ortak import CIKTI, baglam, yerlestir, ShapeBuilder, olcum_yaz

KAT_H = 3.0           # kat yüksekliği (m) — döşemeden döşemeye
TAVAN = 2.5           # asma tavan altı net yükseklik (mahal hacmi bununla); tavan boşluğu 2,50–2,80
# mahal: (No, ad, x0, y0, x1, y1) — metre, kat planı 20 × 12
MAHALLER = [
    ("101", "Açık Ofis", 0, 0, 12, 7),
    ("102", "Toplantı Odası", 12, 0, 20, 7),
    ("103", "Koridor", 0, 7, 20, 9),
    ("104", "Yönetici Odası", 0, 9, 7, 12),
    ("105", "Mutfak", 7, 9, 12, 12),
    ("106", "WC", 12, 9, 16, 12),
    ("107", "Teknik Oda", 16, 9, 20, 12),
]


KIRIS = (5.85, 0, 7)   # (x, y0, y1): açık ofisin ortasında


def kur(mahaller=MAHALLER, kiris=KIRIS, kat_adi="1. Kat", dosya="OFIS-KAT1.ifc"):
    f = api.project.create_file(version="IFC4X3")
    proje = api.root.create_entity(f, ifc_class="IfcProject", name="Örnek Ofis — Mekanik Tesisat Kursu")
    api.unit.assign_unit(f, length={"is_metric": True, "raw": "METERS"})
    body, _ = baglam(f)
    arsa = api.root.create_entity(f, ifc_class="IfcSite", name="Arsa")
    bina = api.root.create_entity(f, ifc_class="IfcBuilding", name="Ofis Binası")
    kat = api.root.create_entity(f, ifc_class="IfcBuildingStorey", name=kat_adi)
    kat.Elevation = 0.0
    api.aggregate.assign_object(f, relating_object=proje, products=[arsa])
    api.aggregate.assign_object(f, relating_object=arsa, products=[bina])
    api.aggregate.assign_object(f, relating_object=bina, products=[kat])
    for e in (arsa, bina, kat):
        yerlestir(f, e)
    sb = ShapeBuilder(f)

    for no, ad, x0, y0, x1, y1 in mahaller:
        m = api.root.create_entity(f, ifc_class="IfcSpace", name=no)
        m.LongName = ad
        api.aggregate.assign_object(f, relating_object=kat, products=[m])
        yerlestir(f, m, x0, y0, 0)
        prof = sb.rectangle(size=(x1 - x0, y1 - y0))
        rep = sb.get_representation(body, [sb.extrude(sb.profile(prof), TAVAN)])
        api.geometry.assign_representation(f, product=m, representation=rep)

    # dış duvarlar (0,2 m) — çakışma kontrolü ve görsel bağlam için
    for (x0, y0, x1, y1) in [(0, 0, 20, 0), (20, 0, 20, 12), (20, 12, 0, 12), (0, 12, 0, 0)]:
        w = api.root.create_entity(f, ifc_class="IfcWall", name="Dış Duvar")
        api.spatial.assign_container(f, relating_structure=kat, products=[w])
        rep = api.geometry.create_2pt_wall(f, element=w, context=body, p1=(x0, y0), p2=(x1, y1), elevation=0, height=KAT_H, thickness=0.2, is_si=True)
        if w.Representation is None:
            api.geometry.assign_representation(f, product=w, representation=rep)
    # döşeme
    d = api.root.create_entity(f, ifc_class="IfcSlab", name="Döşeme")
    api.spatial.assign_container(f, relating_structure=kat, products=[d])
    yerlestir(f, d, 0, 0, KAT_H - 0.2)
    rep = sb.get_representation(body, [sb.extrude(sb.profile(sb.rectangle(size=(20, 12))), 0.2)])
    api.geometry.assign_representation(f, product=d, representation=rep)
    # kiriş K1: açık ofisin ortasında (x = 6), 30 × 35 cm, alt kotu 2,45 — tavan boşluğunu keser (3. hafta çakışma örneği)
    k = api.root.create_entity(f, ifc_class="IfcBeam", name="Kiriş K1")
    api.spatial.assign_container(f, relating_structure=kat, products=[k])
    yerlestir(f, k, kiris[0], kiris[1], 2.45)
    rep = sb.get_representation(body, [sb.extrude(sb.profile(sb.rectangle(size=(0.3, kiris[2] - kiris[1]))), 0.35)])
    api.geometry.assign_representation(f, product=k, representation=rep)

    yol = CIKTI / dosya
    f.write(str(yol))
    olcum_yaz(f"bina:{dosya}", {"dosya": yol.name, "mahal": len(mahaller), "sema": f.schema, "kat_h": KAT_H, "tavan": TAVAN})
    print(yol, f.schema, len(f.by_type("IfcSpace")), "mahal")
    return yol


if __name__ == "__main__":
    kur()
