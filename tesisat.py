"""Tesisat yardımcıları — kanal/boru parçası, bağlantı parçası, port bağlama.
Her parça iki uçlu: port_bas (gelen) ve port_son (giden). Bağlantı = iki portu birbirine bağlamak."""
import numpy as np
import ifcopenshell.api as api
import ifcopenshell.util.system as usys
from ortak import ShapeBuilder, yerlestir


def _matris(p1, p2):
    p1, p2 = np.array(p1, float), np.array(p2, float)
    z = (p2 - p1) / np.linalg.norm(p2 - p1)
    x = np.cross([0, 0, 1], z)
    x = x / np.linalg.norm(x) if np.linalg.norm(x) > 1e-9 else np.array([1.0, 0, 0])
    y = np.cross(z, x)
    m = np.eye(4); m[:3, 0], m[:3, 1], m[:3, 2], m[:3, 3] = x, y, z, p1
    return m


def _portlar(f, eleman, n):
    ps = []
    for i in range(n):
        p = api.system.add_port(f, element=eleman)
        p.FlowDirection = "SINK" if i == 0 else "SOURCE"
        ps.append(p)
    return ps


def parca(f, kat, body, sinif, ad, p1, p2, en, boy=None):
    """Düz kanal (boy verilirse dikdörtgen en × boy) ya da boru (yalnız en = dış çap)."""
    e = api.root.create_entity(f, ifc_class=sinif, name=ad)
    api.spatial.assign_container(f, relating_structure=kat, products=[e])
    api.geometry.edit_object_placement(f, product=e, matrix=_matris(p1, p2), is_si=True)
    sb = ShapeBuilder(f)
    L = float(np.linalg.norm(np.array(p2, float) - np.array(p1, float)))
    if boy is None:   # standart IFC profilleri: ölçü modelden doğrudan okunur (metraj)
        prof = f.create_entity("IfcCircleProfileDef", ProfileType="AREA", Radius=en / 2)
    else:
        prof = f.create_entity("IfcRectangleProfileDef", ProfileType="AREA", XDim=en, YDim=boy)
    api.geometry.assign_representation(f, product=e, representation=sb.get_representation(body, [sb.extrude(prof, L)]))
    bas, son = _portlar(f, e, 2)
    return e, bas, son


def cihaz(f, kat, body, sinif, ad, xyz, olcu, n_port=1):
    """Kutu biçimli cihaz/bağlantı parçası (santral, menfez, dirsek, te, radyatör, kazan)."""
    e = api.root.create_entity(f, ifc_class=sinif, name=ad)
    api.spatial.assign_container(f, relating_structure=kat, products=[e])
    dx, dy, dz = olcu
    yerlestir(f, e, xyz[0] - dx / 2, xyz[1] - dy / 2, xyz[2] - dz / 2)
    sb = ShapeBuilder(f)
    rep = sb.get_representation(body, [sb.extrude(sb.profile(sb.rectangle(size=(dx, dy))), dz)])
    api.geometry.assign_representation(f, product=e, representation=rep)
    return e, _portlar(f, e, n_port)


def bagla(f, kaynak_port, hedef_port):
    api.system.connect_port(f, port1=kaynak_port, port2=hedef_port, direction="SOURCE")


def agi_gez(baslangic):
    """Bir elemandan port bağlantılarını izleyerek ulaşılan tüm elemanları döndürür (ağ bütünlüğü)."""
    gorulen, yigin = set(), [baslangic]
    while yigin:
        e = yigin.pop()
        if e.id() in gorulen:
            continue
        gorulen.add(e.id())
        for p in usys.get_ports(e):
            k = usys.get_connected_port(p)
            if k is not None:
                yigin.append(usys.get_port_element(k))
    return gorulen
