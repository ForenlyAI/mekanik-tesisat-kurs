#!/usr/bin/env python3
"""Hafta 4 — metraj, keşif, BCF ile sorun bildirme, bitirme projesi.
  python lab/hafta4.py → cikti/METRAJ.csv · KESIF.csv · IDS-v1.bcf · TESISAT-KAT1-v3.ifc (miktarlar modelde)
                         · bitirme/ (OFIS-KAT2 üzerinde tüm akış) (+ OLCUMLER.json 'hafta4', 'bitirme')
Birim fiyatlar ÖRNEKTİR [varsayım] — gerçek keşifte güncel birim fiyat listesi kullanılır."""
import csv, math, shutil
from collections import defaultdict
import ifcopenshell, ifcopenshell.api as api
from ifctester import ids, reporter
from ortak import CIKTI, olcum_yaz
import bina, hafta2, hafta3
from tesisat import agi_gez

# örnek birim fiyatlar (TL) [varsayım — yalnız yöntemi göstermek için]
BIRIM_FIYAT = {"kanal_m2": 900, "boru_m": 350, "menfez_adet": 1500, "radyator_adet": 4500,
               "kanal_baglanti_adet": 400, "boru_baglanti_adet": 120}


def _boy(e):
    for r in e.Representation.Representations:
        for it in r.Items:
            if it.is_a("IfcExtrudedAreaSolid"):
                return it.Depth, it.SweptArea
    return 0.0, None


def metraj(yol, cikis_ifc):
    """Kanal: ölçü bazında uzunluk ve sac yüzeyi (çevre × boy); boru: çap bazında uzunluk; diğerleri adet.
    Uzunluk aynı zamanda modele Qto_*BaseQuantities olarak yazılır."""
    f = ifcopenshell.open(str(yol))
    satir = defaultdict(lambda: {"miktar": 0.0, "birim": ""})
    for e in f.by_type("IfcDuctSegment"):
        L, prof = _boy(e)
        en, boy = prof.XDim, prof.YDim
        k = f"Dikdörtgen kanal {round(en * 1000)}×{round(boy * 1000)} mm"
        satir[k]["miktar"] += 2 * (en + boy) * L; satir[k]["birim"] = "m²"
        q = api.pset.add_qto(f, product=e, name="Qto_DuctSegmentBaseQuantities")
        api.pset.edit_qto(f, qto=q, properties={"Length": L})
    for e in f.by_type("IfcPipeSegment"):
        L, prof = _boy(e)
        k = f"Çelik boru Ø{round(prof.Radius * 2000)} mm"
        satir[k]["miktar"] += L; satir[k]["birim"] = "m"
        q = api.pset.add_qto(f, product=e, name="Qto_PipeSegmentBaseQuantities")
        api.pset.edit_qto(f, qto=q, properties={"Length": L})
    for sinif, ad in [("IfcAirTerminal", "Tavan difüzörü"), ("IfcSpaceHeater", "Radyatör"),
                      ("IfcDuctFitting", "Kanal bağlantı parçası"), ("IfcPipeFitting", "Boru bağlantı parçası")]:
        satir[ad]["miktar"] = len(f.by_type(sinif)); satir[ad]["birim"] = "adet"
    f.write(str(cikis_ifc))
    return [{"kalem": k, "miktar": round(v["miktar"], 2), "birim": v["birim"]} for k, v in sorted(satir.items())]


def kesif(met):
    fiyat = {"m²": BIRIM_FIYAT["kanal_m2"], "m": BIRIM_FIYAT["boru_m"]}
    ozel = {"Tavan difüzörü": "menfez_adet", "Radyatör": "radyator_adet",
            "Kanal bağlantı parçası": "kanal_baglanti_adet", "Boru bağlantı parçası": "boru_baglanti_adet"}
    out = []
    for r in met:
        bf = BIRIM_FIYAT[ozel[r["kalem"]]] if r["kalem"] in ozel else fiyat[r["birim"]]
        out.append({**r, "birim_fiyat_tl": bf, "tutar_tl": round(r["miktar"] * bf)})
    out.append({"kalem": "TOPLAM", "miktar": "", "birim": "", "birim_fiyat_tl": "", "tutar_tl": sum(r["tutar_tl"] for r in out)})
    return out


def csv_yaz(yol, rows):
    with open(yol, "w", newline="") as fp:
        w = csv.DictWriter(fp, fieldnames=list(rows[0]), delimiter=";"); w.writeheader(); w.writerows(rows)


def bcf(ids_yol, ifc_yol, cikis):
    k = ids.open(str(ids_yol)); model = ifcopenshell.open(str(ifc_yol)); k.validate(model)  # model rapor bitene kadar bellekte kalmalı
    r = reporter.Bcf(k); r.report(); r.to_file(str(cikis))
    import zipfile
    with zipfile.ZipFile(cikis) as z:
        return sum(1 for n in z.namelist() if n.endswith("markup.bcf"))


# ---- bitirme: ikinci kat, farklı plan, aynı akış
KAT2_MAHAL = [
    ("201", "Eğitim Salonu", 0, 0, 9, 7), ("202", "Ofis", 9, 0, 20, 7), ("203", "Koridor", 0, 7, 20, 9),
    ("204", "Ofis", 0, 9, 10, 12), ("205", "Arşiv", 10, 9, 16, 12), ("206", "Teknik Oda", 16, 9, 20, 12)]
KAT2_KIRIS = (12.85, 0, 7)                               # 202 nolu ofisin içinden geçer
KAT2_HAVA = {"201": 6, "202": 4, "204": 4}
KAT2_RADYATOR = [("201", 4.5, 0.3), ("202", 14.5, 0.3), ("204", 5.0, 11.7)]


def bitirme():
    d = CIKTI / "bitirme"; d.mkdir(exist_ok=True)
    girdi = bina.kur(KAT2_MAHAL, KAT2_KIRIS, "2. Kat", dosya="bitirme/OFIS-KAT2.ifc")
    f = ifcopenshell.open(str(girdi))
    debi, olculer, tasarim, akis, toplam = hafta3.debi_ve_tasarim(f, KAT2_HAVA)
    v = d / "TESISAT-KAT2.ifc"
    ag = hafta2.kur(tasarim, v, girdi, KAT2_RADYATOR)
    hafta3.debi_yaz(v, akis)
    c = hafta3.cakisma(v, d / "CAKISMA.csv")
    s, _ = hafta3.ids_kontrol(CIKTI / "TESISAT-KURALLARI.ids", v, d / "IDS.html")
    met = metraj(v, d / "TESISAT-KAT2-teslim.ifc")
    kes = kesif(met)
    csv_yaz(d / "DEBI-TABLOSU.csv", debi); csv_yaz(d / "KANAL-OLCULERI.csv", olculer)
    csv_yaz(d / "METRAJ.csv", met); csv_yaz(d / "KESIF.csv", kes)
    # "çalışıyor" tanımı (teslim ölçütü)
    olcut = {
        "tum_menfezler_bagli": ag["tum_menfezler_bagli"], "tum_radyatorler_bagli": ag["tum_radyatorler_bagli"],
        "cakisma_0": len(c) == 0, "ids_tamami_gecti": all(s.values()),
        "debi_karsilaniyor": all(r["menfez_adet"] * hafta3.MENFEZ_KAPASITE >= r["debi_m3h"] for r in debi),
        "metraj_dolu": len(met) >= 6,
    }
    return {"toplam_debi_m3h": toplam, "debi": debi, "cakisma": c, "ids": s, "kesif_toplam_tl": kes[-1]["tutar_tl"],
            "olcut": olcut, "GECTI": all(olcut.values())}


if __name__ == "__main__":
    v2 = CIKTI / "TESISAT-KAT1-v2.ifc"
    met = metraj(v2, CIKTI / "TESISAT-KAT1-v3.ifc")
    kes = kesif(met)
    csv_yaz(CIKTI / "METRAJ.csv", met); csv_yaz(CIKTI / "KESIF.csv", kes)
    for r in kes: print(r)
    n_bcf = bcf(CIKTI / "TESISAT-KURALLARI.ids", CIKTI / "TESISAT-KAT1.ifc", CIKTI / "IDS-v1.bcf")
    print("BCF konu sayısı (v1 hataları):", n_bcf)
    olcum_yaz("hafta4", {"metraj": met, "kesif_toplam_tl": kes[-1]["tutar_tl"], "bcf_konu": n_bcf})
    b = bitirme()
    print("BİTİRME:", b["olcut"], "GEÇTİ" if b["GECTI"] else "KALDI", "toplam debi", b["toplam_debi_m3h"])
    olcum_yaz("bitirme", b)
