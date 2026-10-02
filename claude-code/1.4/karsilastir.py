#!/usr/bin/env python3
"""1.4 — Claude Code'un MAHAL.csv'si ile 1.3'teki MAHAL-LISTESI.csv satır satır aynı mı?"""
import csv
a = {r["no"]: (float(r["alan_m2"]), float(r["hacim_m3"])) for r in csv.DictReader(open("../../cikti/MAHAL-LISTESI.csv"), delimiter=";")}
b = {}
for r in csv.reader(open("MAHAL.csv", encoding="utf-8-sig"), delimiter=";"):
    if r[0].isdigit():
        b[r[0]] = (float(r[2]), float(r[3]))
ayni = 0
for no in sorted(a):
    ok = no in b and all(abs(x - y) < 0.01 for x, y in zip(a[no], b[no]))
    ayni += ok
    print(f"{no}  bizim {a[no][0]:6.2f} m² {a[no][1]:7.2f} m³   Claude Code {b.get(no, ('-', '-'))[0]:>6} m² {b.get(no, ('-', '-'))[1]:>7} m³   {'aynı' if ok else 'FARKLI'}")
print(f"sonuç: {ayni}/{len(a)} satır aynı")
