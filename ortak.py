"""Lab ortak yardımcılar — IfcOpenShell 0.9.0 (lab/ortam/SURUM.yml).
Birim: metre. Şema: IFC4X3 (ISO 16739-1:2024)."""
import json, pathlib
import importlib, pkgutil
import ifcopenshell, ifcopenshell.api as api
for _m in pkgutil.iter_modules(api.__path__):
    importlib.import_module(f"ifcopenshell.api.{_m.name}")
from ifcopenshell.util.shape_builder import ShapeBuilder

LAB = pathlib.Path(__file__).resolve().parent
CIKTI = LAB / "cikti"
CIKTI.mkdir(exist_ok=True)
OLCUM = LAB / "OLCUMLER.json"


def olcum_yaz(anahtar, deger):
    d = json.loads(OLCUM.read_text()) if OLCUM.exists() else {}
    d[anahtar] = deger
    OLCUM.write_text(json.dumps(d, ensure_ascii=False, indent=1))


def baglam(f):
    """Model / Body / Axis bağlamlarını döndürür (varsa bulur)."""
    model = next((c for c in f.by_type("IfcGeometricRepresentationContext") if c.ContextType == "Model" and not c.is_a("IfcGeometricRepresentationSubContext")), None)
    if model is None:
        model = api.context.add_context(f, context_type="Model")
    def alt(ident, tip):
        for c in f.by_type("IfcGeometricRepresentationSubContext"):
            if c.ContextIdentifier == ident:
                return c
        return api.context.add_context(f, context_type="Model", context_identifier=ident, target_view=tip, parent=model)
    return alt("Body", "MODEL_VIEW"), alt("Axis", "GRAPH_VIEW")


def yerlestir(f, urun, x=0.0, y=0.0, z=0.0):
    import numpy as np
    m = np.eye(4); m[:3, 3] = (x, y, z)
    api.geometry.edit_object_placement(f, product=urun, matrix=m, is_si=True)
