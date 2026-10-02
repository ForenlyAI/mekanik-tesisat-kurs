#!/usr/bin/env python3
"""2.1 — tesisat modelinde her sınıftan kaç eleman var?  python sinif_say.py TESISAT-KAT1.ifc"""
import sys, ifcopenshell
f = ifcopenshell.open(sys.argv[1])
for sinif in ["IfcDuctSegment", "IfcDuctFitting", "IfcAirTerminal", "IfcUnitaryEquipment",
              "IfcPipeSegment", "IfcPipeFitting", "IfcSpaceHeater", "IfcBoiler",
              "IfcDistributionPort", "IfcDistributionSystem"]:
    print(f"{sinif:24} {len(f.by_type(sinif)):3}")
