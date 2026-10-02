# BIM ile Mekanik Tesisat 101 — kurs dosyaları

Forenly AI Academy kursunun uygulama dosyaları. IFC 4.3 (ISO 16739-1:2024) model, IfcOpenShell 0.9.0.

## Ortamı açmak
- **Tek tık:** GitHub'da **Code → Codespaces → Create codespace**. Kurulum kendiliğinden yapılır.
- **Kendi bilgisayarınız (Python 3.10+):**
  ```
  python -m venv ifc
  source ifc/bin/activate        # Windows: ifc\Scripts\activate
  pip install -r requirements.txt
  ```

## Haftalar
| komut | ne yapar | çıktı (cikti/) |
|---|---|---|
| `python bina.py` | 1. kat mimari modeli | OFIS-KAT1.ifc |
| `python hafta1.py` | hiyerarşi + mahal listesi | HIYERARSI.txt · MAHAL-LISTESI.csv |
| `python hafta2.py` | havalandırma + ısıtma, bağlantı kontrolü | TESISAT-KAT1.ifc |
| `python sinif_say.py cikti/TESISAT-KAT1.ifc` | sınıf sayımı (2.1) | — |
| `python olumsuz_test.py cikti/TESISAT-KAT1.ifc` | olumsuz test (2.4) | — |
| `python hafta3.py` | debi, kanal ölçüsü, çakışma, IDS | DEBI-TABLOSU.csv · KANAL-OLCULERI.csv · CAKISMA-*.csv · IDS-*.html |
| `python hafta4.py` | metraj, keşif, BCF, bitirme (2. kat) | METRAJ.csv · KESIF.csv · IDS-v1.bcf · bitirme/ |

Claude Code alıştırması (1.4): `claude-code/1.4/ISTEM.txt` istemini Claude Code'a verin, sonra `python karsilastir.py`.

**Not:** hava değişim sayıları, menfez kapasitesi, hızlar ve birim fiyatlar ÖRNEKTİR. Gerçek projede şartname ve güncel fiyat listesi kullanılır.
