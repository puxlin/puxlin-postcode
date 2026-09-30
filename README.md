# puxlin-postcode

Puxlin için Belçika bölgesel referans ağacı (country → region → province → arrondissement → municipality → postal_code) ve Hollanda öneri dosyası.

## Klasör yapısı
- `output/<YYYY-MM>/areas.json` – ana liste (BE + `NL` ülke satırı)
- `output/<YYYY-MM>/areas_diff.json` – önceki sürüme göre added / removed / renamed / reparented
- `output/<YYYY-MM>/rapor.txt` – kaynaklar, sayılar, hariç tutulanlar, belirsizlikler
- `output/<YYYY-MM>/areas_nl_proposal.json` + `rapor_nl.txt` – Hollanda önerisi (ana listeyle birleştirilmez)
- `output/<YYYY-MM>/_log.json` – derleme günlüğü (raporun ham girdisi)
- `tools/` – derleme ve doğrulama betikleri, `sources_state.json` (son kontrol edilen kaynak tarihleri)

Önceki sürümler silinmez; her ay yeni klasör açılır.

## Yeniden üretme
1. Kaynakları indir (URL'ler `tools/sources_state.json` ve raporda): Statbel REFNIS xlsx, bpost `zipcodes_num_nl/fr_*.xls`, BeSt OpenAddress CSV'leri, CBS gemeenten xlsx ve pc6hnr zip → `sources/`
2. `python3 tools/aggregate_best.py <openaddress klasörü>`
3. `python3 tools/build_be.py YYYY-MM output/YYYY-MM`
4. `python3 tools/validate_report.py output/YYYY-MM output/<önceki>/areas.json`
5. `python3 tools/build_nl.py YYYY-MM output/YYYY-MM <pc6hnr.csv> <gem_YYYY.csv>`
