#!/usr/bin/env python3
"""Usage: validate_report.py <outdir> [<prev areas.json>]  -> writes areas_diff.json, rapor.txt"""
import json, os, re, sys, collections
OUT=sys.argv[1]; PREV=sys.argv[2] if len(sys.argv)>2 else None
doc=json.load(open(os.path.join(OUT,'areas.json'),encoding='utf-8')); A=doc['areas']; LOG=json.load(open(os.path.join(OUT,'_log.json'),encoding='utf-8'))
by={a['code']:a for a in A}; ORDER=['country','region','province','arrondissement','municipality','postal_code']
FMT={'country':r'[A-Z]{2}','region':r'BE-(VLG|WAL|BRU)','province':r'BE-[VW][A-Z]{2}','arrondissement':r'BE-ARR-\d{5}','municipality':r'BE-MUN-\d{5}','postal_code':r'BE-PC-\d{4}'}
err=[]
codes=[a['code'] for a in A]
if len(codes)!=len(set(codes)): err.append('Tekrar eden kod var: '+str([c for c,n in collections.Counter(codes).items() if n>1]))
for a in A:
    c,l,p=a['code'],a['level'],a['parent']
    if not re.fullmatch(FMT[l],c): err.append(f'{c}: biçim hatalı')
    if (p is None)!=(l=='country'): err.append(f'{c}: parent null kuralı ihlali')
    if p is not None:
        if p not in by: err.append(f'{c}: parent {p} listede yok'); continue
        exp=ORDER[ORDER.index(l)-1]; pl=by[p]['level']
        if pl!=exp and not (c=='BE-ARR-21000' and p=='BE-BRU'): err.append(f'{c}: parent seviyesi {pl}, beklenen {exp}')
    seen=set(); x=a
    while x['parent'] is not None:
        if x['code'] in seen: err.append(f'{c}: döngü'); break
        seen.add(x['code']); x=by.get(x['parent'],{'parent':None,'level':'?','code':'?'})
    if x['level']!='country': err.append(f'{c}: zincir ülkede bitmiyor')
    if ('places' in a)!=(l=='postal_code'): err.append(f'{c}: places kuralı ihlali')
    if not a['names']: err.append(f'{c}: isim yok')
    # official language
    chain=[]; x=a
    while x: chain.append(x['code']); x=by.get(x['parent']) if x['parent'] else None
    need=[]
    if c.startswith('BE') and l!='country':
        if 'BE-VLG' in chain: need=['nl']
        elif 'BE-BRU' in chain: need=['nl','fr']
        elif 'BE-WAL' in chain: need=['fr']
    elif c=='BE': need=['nl','fr','de']
    elif c=='NL': need=['nl']
    for lg in need:
        if lg not in a['names']: err.append(f'{c}: resmi dilde ({lg}) isim yok')
bru=[a for a in A if a['code']=='BE-ARR-21000'][0]
if bru['parent']!='BE-BRU': err.append('BE-ARR-21000 parent BE-BRU değil')
cnt=collections.Counter(a['level'] for a in A)
munis_with_pc={a['parent'] for a in A if a['level']=='postal_code'}
no_pc=[a for a in A if a['level']=='municipality' and a['code'] not in munis_with_pc]
for m in no_pc: err.append(f"{m['code']} {m['names'].get('nl') or m['names'].get('fr')}: hiçbir posta kodunun parent'ı değil (ör. kodunu daha büyük bir belediyeyle paylaşıyor olabilir)")
sanity=[]
if cnt['region']!=3: sanity.append(f"Bölge sayısı {cnt['region']} (beklenen 3)")
if cnt['province']!=10: sanity.append(f"İl sayısı {cnt['province']} (beklenen 10)")
if cnt['municipality']!=565: sanity.append(f"Belediye sayısı {cnt['municipality']} (1.1.2025 itibarıyla beklenen 565)")
if cnt['arrondissement']!=43: sanity.append(f"Arrondissement sayısı {cnt['arrondissement']} (beklenen 43)")
# ---- diff
prev=json.load(open(PREV,encoding='utf-8')) if PREV else None
diff={'from':prev['version'] if prev else None,'to':doc['version'],'added':[],'removed':[],'renamed':[],'reparented':[]}
pcnt=collections.Counter()
if prev:
    pb={a['code']:a for a in prev['areas']}; pcnt=collections.Counter(a['level'] for a in prev['areas'])
    diff['added']=sorted(set(by)-set(pb)); diff['removed']=sorted(set(pb)-set(by))
    for c in sorted(set(by)&set(pb)):
        if by[c]['names']!=pb[c]['names']: diff['renamed'].append({'code':c,'old':pb[c]['names'],'new':by[c]['names']})
        if by[c]['parent']!=pb[c]['parent']: diff['reparented'].append({'code':c,'old':pb[c]['parent'],'new':by[c]['parent']})
json.dump(diff,open(os.path.join(OUT,'areas_diff.json'),'w',encoding='utf-8'),ensure_ascii=False,indent=1)
# ---- report
R=[]; w=R.append
w(f"PUXLIN – BELÇİKA BÖLGESEL REFERANS VERİSİ RAPORU\nSürüm: {doc['version']}   Önceki sürüm: {diff['from'] or '(yok – ilk çalıştırma)'}\n")
w("1. SİLİNEN KODLAR (en üstte)")
if not prev: w("   İlk çalıştırma: karşılaştırılacak önceki sürüm yok, silinen kod yok.")
elif not diff['removed']: w("   Silinen kod yok.")
else:
    for c in diff['removed']: w(f"   - {c}  → yerine geçen: {LOG.get('successor',{}).get(c,'(belirlenemedi – kontrol edin)')}")
w("")
w("2. KAYNAKLAR"); [w('   '+s) for s in LOG.get('source_lines',[])]; [w('   Not: '+s) for s in LOG.get('sources',[])]; w("")
w("3. SATIR SAYILARI (seviye: bu sürüm / önceki / fark)")
for l in ORDER: w(f"   {l:15s} {cnt[l]:5d} / {pcnt[l] if prev else '-':>5} / {cnt[l]-pcnt[l] if prev else '-'}")
w(f"   {'TOPLAM':15s} {len(A):5d}")
if prev: w(f"   Eklenen {len(diff['added'])}, silinen {len(diff['removed'])}, yeniden adlandırılan {len(diff['renamed'])}, parent'ı değişen {len(diff['reparented'])}")
w("")
w("4. HARİÇ TUTULAN POSTA KODLARI"); [w('   - '+s) for s in LOG.get('excluded',[])]; [w('   ! '+s) for s in LOG.get('excluded_note',[])]; w("")
w("5. BİRDEN FAZLA BELEDİYEYE DÜŞEN POSTA KODLARI")
w("   a) bpost yerlerine göre (kuralın uygulandığı durumlar):")
[w('   - '+s) for s in LOG.get('multi',[])] or w("   - Yok: bpost listesinde her posta kodunun tüm yerleri tek bir hoofdgemeente'ye bağlı.")
w("   b) BeSt adreslerine göre (bilgi amaçlı; parent bpost kuralıyla verildi):"); [w('   - '+s) for s in LOG.get('best_span',[])]; w("")
w("6. DOĞRULAMA (bölüm 6)")
w("   Tüm kontroller geçti." if not err else f"   {len(err)} kontrol geçmedi:"); [w('   ✗ '+e) for e in err]
[w('   ! Sayı uyumsuzluğu: '+s) for s in sanity] if sanity else w("   Sayılar bilinen yapıyla uyumlu: 3 bölge, 10 il, 43 arrondissement, 565 belediye.")
w("")
w("7. BELİRSİZLİKLER"); [w('   - '+s) for s in LOG.get('ambiguous',[])+LOG.get('uncertain',[])]; w("")
w("8. VERİ KARARLARI / NOTLAR"); [w('   - '+s) for s in LOG.get('decisions',[])]
open(os.path.join(OUT,'rapor.txt'),'w',encoding='utf-8').write('\n'.join(R)+'\n')
print('errors',len(err)); print('\n'.join(err[:30])); print(sanity)
