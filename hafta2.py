#!/usr/bin/env python3
"""Hafta 2 — mimari modele mekanik tesisat eklemek: havalandırma kanalı, menfez, ısıtma borusu, radyatör, sistem ve bağlantılar.
  python lab/hafta2.py → cikti/TESISAT-KAT1.ifc (+ OLCUMLER.json 'hafta2')
İlk tasarım: her beslenen mahalde ORTADA tek menfez (boyut tahmini). 3. hafta hesapla düzeltir."""
import ifcopenshell, ifcopenshell.api as api
from ortak import CIKTI, baglam, olcum_yaz
from tesisat import parca, cihaz, bagla, agi_gez

Z_KANAL = 2.65     # kanal ekseni: tavan boşluğu 2,50–2,80 (kanal 20 cm → 2,55–2,75)
Z_MENFEZ = 2.50    # menfez asma tavan seviyesinde
Z_BORU = 0.15      # ısıtma borusu döşeme üstü

ILK_TASARIM = {
    "ana_kanal": (0.40, 0.20),          # en × boy (m) — tahmin
    "dal_kanal": {},                     # boş = varsayılan (0.25, 0.20)
    "menfezler": [                       # (mahal, x, y)
        ("101", 6.0, 3.5), ("102", 16.0, 3.5), ("104", 3.5, 10.5)],
}
RADYATORLER = [("101", 3.0, 0.3), ("101", 9.0, 0.3), ("102", 16.0, 0.3), ("104", 3.5, 11.7)]


def ag(f, kat, body, sistem, ilk_port, kose, ana_y, z, dallar, seg, fit, ana_olcu, dal_olcu):
    """Ana hat y = ana_y boyunca batıya ilerler; her dal (x, y_uc) noktasındaki uç cihaza iner.
    dal_olcu(i) → (en, boy|None); ana_olcu(i) → i. ana parçanın ölçüsü."""
    elemanlar = []
    dallar = sorted(dallar, key=lambda d: -d["x"])
    # köşe dirseği: yükselen hattan ana hatta
    dirsek, (d_in, d_out) = cihaz(f, kat, body, fit, "Dirsek", (kose[0], ana_y, z), (0.3, 0.3, 0.3), 2)
    dirsek.PredefinedType = "BEND"
    bagla(f, ilk_port, d_in)
    elemanlar.append(dirsek)
    onceki_port, onceki_x = d_out, kose[0]
    for i, d in enumerate(dallar):
        en, boy = ana_olcu(i)
        s, s_in, s_out = parca(f, kat, body, seg, f"Ana hat {i + 1}", (onceki_x, ana_y, z), (d["x"], ana_y, z), en, boy)
        bagla(f, onceki_port, s_in)
        son = i == len(dallar) - 1
        b, ports = cihaz(f, kat, body, fit, "Dirsek" if son else "Te", (d["x"], ana_y, z), (0.3, 0.3, 0.3), 2 if son else 3)
        b.PredefinedType = "BEND" if son else "JUNCTION"
        bagla(f, s_out, ports[0])
        den, dboy = dal_olcu(d)
        ds, ds_in, ds_out = parca(f, kat, body, seg, f"Dal {d['ad']}", (d["x"], ana_y, z), (d["x"], d["y"], z), den, dboy)
        bagla(f, ports[-1], ds_in)
        uc, (uc_in,) = cihaz(f, kat, body, d["sinif"], d["ad"], (d["x"], d["y"], d["z"]), d["olcu"], 1)
        if d.get("tip"):
            uc.PredefinedType = d["tip"]
        bagla(f, ds_out, uc_in)
        elemanlar += [s, b, ds, uc]
        onceki_port, onceki_x = (ports[1], d["x"]) if not son else (None, d["x"])
    api.system.assign_system(f, products=elemanlar, system=sistem)
    return elemanlar


def kur(tasarim, cikis, girdi=CIKTI / "OFIS-KAT1.ifc", radyatorler=RADYATORLER):
    f = ifcopenshell.open(str(girdi))
    kat = f.by_type("IfcBuildingStorey")[0]
    body, _ = baglam(f)

    # --- havalandırma (besleme) sistemi
    hava = api.system.add_system(f, ifc_class="IfcDistributionSystem")
    hava.Name, hava.PredefinedType = "Taze Hava Besleme", "VENTILATION"
    santral, (s_out,) = cihaz(f, kat, body, "IfcUnitaryEquipment", "Havalandırma Santrali", (18.8, 10.5, 0.8), (1.2, 1.0, 1.6), 1)
    santral.PredefinedType = "AIRHANDLER"
    s_out.FlowDirection = "SOURCE"
    ana_en, ana_boy = tasarim["ana_kanal"]
    yukselen, y_in, y_out = parca(f, kat, body, "IfcDuctSegment", "Yükselen kanal", (19.2, 10.5, 1.6), (19.2, 10.5, Z_KANAL), ana_en, ana_boy)
    bagla(f, s_out, y_in)
    d2, (d2_in, d2_out) = cihaz(f, kat, body, "IfcDuctFitting", "Dirsek", (19.2, 10.5, Z_KANAL), (0.3, 0.3, 0.3), 2)
    d2.PredefinedType = "BEND"
    bagla(f, y_out, d2_in)
    kol, k_in, k_out = parca(f, kat, body, "IfcDuctSegment", "Bağlantı kanalı", (19.2, 10.5, Z_KANAL), (19.2, 8.0, Z_KANAL), ana_en, ana_boy)
    bagla(f, d2_out, k_in)
    menfez_dallari = [dict(x=x, y=y, z=Z_MENFEZ, ad=f"Menfez {m}-{i + 1}", mahal=m, sinif="IfcAirTerminal", tip="DIFFUSER", olcu=(0.6, 0.6, 0.1))
                      for i, (m, x, y) in enumerate(tasarim["menfezler"])]
    ana_olculer = tasarim.get("ana_olculer")
    hava_ag = ag(f, kat, body, hava, k_out, (19.2, 8.0), 8.0, Z_KANAL, menfez_dallari, "IfcDuctSegment", "IfcDuctFitting",
                 (lambda i: ana_olculer[i]) if ana_olculer else (lambda i: (ana_en, ana_boy)),
                 lambda d: tasarim["dal_kanal"].get(d["ad"], (0.25, 0.20)))
    api.system.assign_system(f, products=[santral, yukselen, d2, kol], system=hava)

    # --- ısıtma (gidiş) sistemi
    isi = api.system.add_system(f, ifc_class="IfcDistributionSystem")
    isi.Name, isi.PredefinedType = "Isıtma Gidiş", "HEATING"
    kazan, (kz_out,) = cihaz(f, kat, body, "IfcBoiler", "Kazan", (18.0, 11.2, 0.5), (0.6, 0.5, 1.0), 1)
    kz_out.FlowDirection = "SOURCE"
    b1, b1_in, b1_out = parca(f, kat, body, "IfcPipeSegment", "Kazan çıkışı", (18.0, 11.2, Z_BORU), (18.0, 8.6, Z_BORU), 0.042)
    bagla(f, kz_out, b1_in)
    rad_dallari = [dict(x=x, y=y, z=0.45, ad=f"Radyatör {m}-{i + 1}", mahal=m, sinif="IfcSpaceHeater", tip="CONVECTOR", olcu=(1.2, 0.1, 0.6))
                   for i, (m, x, y) in enumerate(radyatorler)]
    isi_ag = ag(f, kat, body, isi, b1_out, (18.0, 8.6), 8.6, Z_BORU, rad_dallari, "IfcPipeSegment", "IfcPipeFitting",
                lambda i: (0.042, None), lambda d: (0.027, None))
    api.system.assign_system(f, products=[kazan, b1], system=isi)

    f.write(str(cikis))
    # ağ bütünlüğü: kaynaktan port izlenerek her uca ulaşılıyor mu?
    hava_ulasilan = agi_gez(santral)
    isi_ulasilan = agi_gez(kazan)
    menfez_ok = all(m.id() in hava_ulasilan for m in f.by_type("IfcAirTerminal"))
    rad_ok = all(r.id() in isi_ulasilan for r in f.by_type("IfcSpaceHeater"))
    sayim = {c: len(f.by_type(c)) for c in ["IfcDuctSegment", "IfcDuctFitting", "IfcAirTerminal", "IfcPipeSegment", "IfcPipeFitting", "IfcSpaceHeater", "IfcDistributionPort"]}
    return {"dosya": cikis.name, "sayim": sayim, "hava_ag_eleman": len(hava_ulasilan), "isi_ag_eleman": len(isi_ulasilan),
            "tum_menfezler_bagli": menfez_ok, "tum_radyatorler_bagli": rad_ok}


if __name__ == "__main__":
    s = kur(ILK_TASARIM, CIKTI / "TESISAT-KAT1.ifc")
    print(s)
    olcum_yaz("hafta2", s)
