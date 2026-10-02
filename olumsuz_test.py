#!/usr/bin/env python3
"""2.4 — olumsuz test: bir menfezin bağlantısını kopar, kontrol bunu yakalıyor mu?  python olumsuz_test.py TESISAT-KAT1.ifc"""
import sys, ifcopenshell, ifcopenshell.api.system
import ifcopenshell.util.system as us
from tesisat import agi_gez
f = ifcopenshell.open(sys.argv[1])
santral = f.by_type("IfcUnitaryEquipment")[0]
menfezler = f.by_type("IfcAirTerminal")
print("önce  — bağlı menfez:", sum(m.id() in agi_gez(santral) for m in menfezler), "/", len(menfezler))
hedef = [m for m in menfezler if m.Name.startswith("Menfez 101")][0]
ifcopenshell.api.system.disconnect_port(f, port=us.get_ports(hedef)[0])
print("kopardık:", hedef.Name)
ulasilan = agi_gez(santral)
for m in menfezler:
    print(f"  {m.Name:14} {'bağlı' if m.id() in ulasilan else 'KOPUK — KALDI'}")
