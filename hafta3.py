#!/usr/bin/env python3
"""Hafta 3 — hesap ve kontrol: hava debisi, kanal boyutlandırma, çakışma kontrolü, IDS ile kural kontrolü.
  python lab/hafta3.py → cikti/DEBI-TABLOSU.csv · KANAL-OLCULERI.csv · TESISAT-KAT1-v2.ifc
                         · CAKISMA-v1.csv / CAKISMA-v2.csv · TESISAT-KURALLARI.ids · IDS-v1.html / IDS-v2.html
Tasarım değerleri (hava değişim sayısı, menfez kapasitesi, hava hızı) ÖRNEK proje şartnamesidir [varsayım];
gerçek projede şartname / yönetmelik / üretici kataloğu verir. Yöntem değişmez, sayılar değişir."""
import csv, math
import ifcopenshell, ifcopenshell.geom, ifcopenshell.api as api
from ifctester import ids, reporter
from ortak import CIKTI, olcum_yaz
import hafta2

# ---- örnek proje şartnamesi [varsayım]
HAVA_DEGISIM = {"101": 4, "102": 6, "104": 4}   # 1/saat; yalnız beslenen mahaller (WC/mutfak egzozu ayrı sistem)
MENFEZ_KAPASITE = 500                            # m³/h, bir tavan difüzörü (katalog değeri örneği)
HIZ_ANA, HIZ_DAL = 5.0, 3.0                      # m/s, konfor uygulaması için seçilen hızlar
KANAL_BOY = 0.20                                 # m, tavan boşluğuna sığan kanal yüksekliği
ADIM = 0.05                                      # m, kanal eni 5 cm katlarına yuvarlanır


def mahaller(f):
    ayar = ifcopenshell.geom.settings(); ayar.set("use-world-coords", True)
    import ifcopenshell.util.shape as us
    out = {}
    for m in f.by_type("IfcSpace"):
        g = ifcopenshell.geom.create_shape(ayar, m).geometry
        xs = g.verts[0::3]; ys = g.verts[1::3]
        out[m.Name] = dict(ad=m.LongName, hacim=us.get_volume(g), x0=min(xs), x1=max(xs), y0=min(ys), y1=max(ys))
    return out


def kanal_eni(debi_m3h, hiz):
    alan = debi_m3h / 3600 / hiz                 # m²  (Q = A · v)
    return max(ADIM * 3, math.ceil(alan / KANAL_BOY / ADIM) * ADIM)


def debi_ve_tasarim(f, hava_degisim=HAVA_DEGISIM):
    m = mahaller(f)
    satir, menfezler = [], []
    for no, n in hava_degisim.items():
        q = m[no]["hacim"] * n
        adet = math.ceil(q / MENFEZ_KAPASITE)
        w = m[no]["x1"] - m[no]["x0"]
        yc = (m[no]["y0"] + m[no]["y1"]) / 2
        for i in range(adet):                    # menfezler mahal boyunca eşit aralıkla
            menfezler.append((no, round(m[no]["x0"] + w * (i + 0.5) / adet, 2), round(yc, 2), q / adet))
        satir.append(dict(mahal=no, ad=m[no]["ad"], hacim_m3=round(m[no]["hacim"], 1), hava_degisim=n,
                          debi_m3h=round(q), menfez_adet=adet, menfez_basina=round(q / adet)))
    # kanal ölçüleri: dal = menfez debisi; ana hat parçası i = kendisinden sonraki tüm dalların toplamı
    sirali = sorted(menfezler, key=lambda t: -t[1])
    ana, dal, olculer = [], {}, []
    for i in range(len(sirali)):
        q = sum(t[3] for t in sirali[i:])
        ana.append((kanal_eni(q, HIZ_ANA), KANAL_BOY))
        olculer.append(dict(parca=f"Ana hat {i + 1}", debi_m3h=round(q), hiz=HIZ_ANA, en_mm=round(ana[-1][0] * 1000), boy_mm=200))
    for j, (no, x, y, q) in enumerate(menfezler):
        ad = f"Menfez {no}-{j + 1}"
        dal[ad] = (kanal_eni(q, HIZ_DAL), KANAL_BOY)
        olculer.append(dict(parca=f"Dal {ad}", debi_m3h=round(q), hiz=HIZ_DAL, en_mm=round(dal[ad][0] * 1000), boy_mm=200))
    toplam = sum(r["debi_m3h"] for r in satir)
    tasarim = {"ana_kanal": (kanal_eni(toplam, HIZ_ANA), KANAL_BOY), "ana_olculer": ana, "dal_kanal": dal,
               "menfezler": [(no, x, y) for no, x, y, _ in menfezler]}
    akis = {r["parca"]: (r["debi_m3h"], r["hiz"]) for r in olculer}
    akis["Yükselen kanal"] = akis["Bağlantı kanalı"] = (toplam, HIZ_ANA)
    for j, (no, x, y, q) in enumerate(menfezler):
        akis[f"Menfez {no}-{j + 1}"] = (round(q), None)
    return satir, olculer, tasarim, akis, toplam


def debi_yaz(yol, akis):
    """Kanal ve menfezlere FRN_Tesisat özellik setini yazar (IDS bunu arar)."""
    f = ifcopenshell.open(str(yol))
    for e in f.by_type("IfcDuctSegment") + f.by_type("IfcAirTerminal"):
        if e.Name in akis:
            q, v = akis[e.Name]
            ps = api.pset.add_pset(f, product=e, name="FRN_Tesisat")
            props = {"HavaDebisi": float(q)}
            if v:
                props["HavaHizi"] = float(v)
            api.pset.edit_pset(f, pset=ps, properties=props)
    f.write(str(yol))


def cakisma(yol, rapor):
    f = ifcopenshell.open(str(yol))
    ayar = ifcopenshell.geom.settings()
    agac = ifcopenshell.geom.tree(backend="opencascade.trianglebvh")
    it = ifcopenshell.geom.iterator(ayar, f, include=f.by_type("IfcDuctSegment") + f.by_type("IfcBeam") + f.by_type("IfcAirTerminal"))
    if it.initialize():
        while True:
            agac.add_element(it.get())
            if not it.next():
                break
    sonuc = agac.clash_intersection_many(f.by_type("IfcDuctSegment") + f.by_type("IfcAirTerminal"), f.by_type("IfcBeam"), tolerance=0.002, check_all=True)
    satirlar = []
    for c in sonuc:
        a, b = f.by_guid(c.a.get_argument(0)), f.by_guid(c.b.get_argument(0))
        satirlar.append(dict(a=a.Name, b=b.Name, derinlik_mm=round(c.distance * 1000), x=round(c.p1[0], 2), y=round(c.p1[1], 2), z=round(c.p1[2], 2)))
    with open(rapor, "w", newline="") as fp:
        w = csv.DictWriter(fp, fieldnames=["a", "b", "derinlik_mm", "x", "y", "z"], delimiter=";")
        w.writeheader(); w.writerows(satirlar)
    return satirlar


def ids_dosyasi(yol):
    k = ids.Ids(title="Mekanik tesisat teslim kuralları", author="Forenly AI Academy", version="1.0",
                description="Kanal ve menfezlerde hava debisi; mahallerde ad", purpose="Kurs Hafta 3 — kural kontrolü")
    s1 = ids.Specification(name="Her kanal parçasının hava debisi var", ifcVersion=["IFC4X3_ADD2"], minOccurs=1)
    s1.applicability.append(ids.Entity(name="IFCDUCTSEGMENT"))
    s1.requirements.append(ids.Property(propertySet="FRN_Tesisat", baseName="HavaDebisi", dataType="IFCREAL"))
    s2 = ids.Specification(name="Her menfezin hava debisi var", ifcVersion=["IFC4X3_ADD2"], minOccurs=1)
    s2.applicability.append(ids.Entity(name="IFCAIRTERMINAL"))
    s2.requirements.append(ids.Property(propertySet="FRN_Tesisat", baseName="HavaDebisi", dataType="IFCREAL"))
    s3 = ids.Specification(name="Her mahalin adı var", ifcVersion=["IFC4X3_ADD2"], minOccurs=1)
    s3.applicability.append(ids.Entity(name="IFCSPACE"))
    s3.requirements.append(ids.Attribute(name="LongName"))
    k.specifications += [s1, s2, s3]
    k.to_xml(str(yol))
    return yol


def ids_kontrol(ids_yol, ifc_yol, html):
    k = ids.open(str(ids_yol))
    model = ifcopenshell.open(str(ifc_yol))  # rapor bitene kadar bellekte kalmalı
    k.validate(model)
    r = reporter.Html(k); r.report(); r.to_file(str(html))
    j = reporter.Json(k); j.report()
    return {s["name"]: s["status"] for s in j.results["specifications"]}, k


if __name__ == "__main__":
    v1 = CIKTI / "TESISAT-KAT1.ifc"
    f = ifcopenshell.open(str(CIKTI / "OFIS-KAT1.ifc"))
    debi, olculer, tasarim, akis, toplam = debi_ve_tasarim(f)
    for ad, rows in [("DEBI-TABLOSU.csv", debi), ("KANAL-OLCULERI.csv", olculer)]:
        with open(CIKTI / ad, "w", newline="") as fp:
            w = csv.DictWriter(fp, fieldnames=list(rows[0]), delimiter=";"); w.writeheader(); w.writerows(rows)
    for r in debi: print(r)
    for r in olculer: print(r)
    v2 = CIKTI / "TESISAT-KAT1-v2.ifc"
    ag = hafta2.kur(tasarim, v2)
    debi_yaz(v2, akis)
    c1 = cakisma(v1, CIKTI / "CAKISMA-v1.csv")
    c2 = cakisma(v2, CIKTI / "CAKISMA-v2.csv")
    print("çakışma v1:", c1); print("çakışma v2:", c2)
    ids_yol = ids_dosyasi(CIKTI / "TESISAT-KURALLARI.ids")
    s1, _ = ids_kontrol(ids_yol, v1, CIKTI / "IDS-v1.html")
    s2, _ = ids_kontrol(ids_yol, v2, CIKTI / "IDS-v2.html")
    print("IDS v1:", s1); print("IDS v2:", s2)
    olcum_yaz("hafta3", {"toplam_debi_m3h": toplam, "debi": debi, "kanal": olculer, "ag_v2": ag,
                         "cakisma_v1": c1, "cakisma_v2": c2, "ids_v1": s1, "ids_v2": s2})
