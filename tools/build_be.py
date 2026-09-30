#!/usr/bin/env python3
"""Puxlin BE areas builder. Usage: build_be.py <version YYYY-MM> <outdir> [<prev areas.json>]
Reads sources from ../sources and BeSt CSVs from ../ (postcode folder)."""
import pandas as pd, json, os, re, sys, unicodedata, collections
BASE=os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC=os.path.join(BASE,'sources')
VERSION, OUT = sys.argv[1], sys.argv[2]
PREV = sys.argv[3] if len(sys.argv)>3 else None
os.makedirs(OUT,exist_ok=True)
LOG=collections.defaultdict(list)   # report sections

# ---------- REFNIS ----------
r=pd.read_excel(os.path.join(SRC,'TU_COM_REFNIS-20250101.xlsx'),dtype=str)
cur=r[r.DT_VLDT_END.astype(str).str.contains('9999')].copy()
retired=r[r.DT_VLDT_END.astype(str).str.contains('2024')].copy()
REGION_ISO={'02000':'BE-VLG','03000':'BE-WAL','04000':'BE-BRU'}
PROV_ISO={'10000':'BE-VAN','20001':'BE-VBR','20002':'BE-WBR','30000':'BE-VWV','40000':'BE-VOV',
          '50000':'BE-WHT','60000':'BE-WLG','70000':'BE-VLI','80000':'BE-WLX','90000':'BE-WNA'}
EN={'BE':'Belgium','NL':'Netherlands','BE-VLG':'Flemish Region','BE-WAL':'Walloon Region','BE-BRU':'Brussels-Capital Region',
    'BE-VAN':'Antwerp','BE-VBR':'Flemish Brabant','BE-WBR':'Walloon Brabant','BE-VWV':'West Flanders','BE-VOV':'East Flanders',
    'BE-ARR-11000':'Antwerp','BE-ARR-21000':'Brussels-Capital','BE-ARR-31000':'Bruges','BE-ARR-35000':'Ostend','BE-ARR-44000':'Ghent',
    'BE-MUN-11002':'Antwerp','BE-MUN-21004':'Brussels','BE-MUN-31005':'Bruges','BE-MUN-35013':'Ostend','BE-MUN-44021':'Ghent'}
GERMAN={'63001','63012','63013','63023','63040','63048','63061','63067','63087'}
def strip_prefix(s,lvl):
    s=str(s).strip()
    pats={'2':[r'^Provincie ',r'^Province (de la |de |du |d’|d\')',r'^Provinz '],
          '3':[r'^Arrondissement (de |d’|d\')?',r'^Bezirk ']}.get(lvl,[])
    for p in pats: s=re.sub(p,'',s)
    return s
code_of={}
for _,x in cur.iterrows():
    c,l=x.CD_REFNIS,x.LVL_REFNIS
    code_of[c]= REGION_ISO[c] if l=='1' else PROV_ISO[c] if l=='2' else f'BE-ARR-{c}' if l=='3' else f'BE-MUN-{c}'
region_of={}
def region_for(c):
    x=cur[cur.CD_REFNIS==c].iloc[0]
    while x.LVL_REFNIS!='1': x=cur[cur.CD_REFNIS==x.CD_SUP_REFNIS].iloc[0]
    return x.CD_REFNIS
areas={}
def add(code,level,parent,names,places=None):
    if code in areas: LOG['validation'].append(f'Tekrar eden kod: {code}')
    d={'code':code,'level':level,'parent':parent,'names':names}
    if places is not None: d['places']=places
    areas[code]=d
add('BE','country',None,{'nl':'België','fr':'Belgique','de':'Belgien','en':EN['BE']})
add('NL','country',None,{'nl':'Nederland','en':EN['NL']})
LVL={'1':'region','2':'province','3':'arrondissement','4':'municipality'}
muni_lang={}
for _,x in cur.sort_values('LVL_REFNIS').iterrows():
    c,l=x.CD_REFNIS,x.LVL_REFNIS; code=code_of[c]
    parent='BE' if l=='1' else code_of.get(x.CD_SUP_REFNIS)
    if parent is None: LOG['validation'].append(f'{code}: REFNIS üst kodu {x.CD_SUP_REFNIS} güncel listede yok')
    names={}
    for lg,col in [('nl','TX_REFNIS_NL'),('fr','TX_REFNIS_FR'),('de','TX_REFNIS_DE')]:
        v=x[col]
        if isinstance(v,str) and v.strip(): names[lg]=strip_prefix(v,l)
    if code in EN and EN[code] not in names.values(): names['en']=EN[code]
    add(code,LVL[l],parent,names)
    if l=='4':
        rg=region_for(c)
        muni_lang[c]= ['nl'] if rg=='02000' else ['nl','fr'] if rg=='04000' else (['fr','de'] if c in GERMAN else ['fr'])
MUNIS=set(cur[cur.LVL_REFNIS=='4'].CD_REFNIS)

# ---------- bpost ----------
def rb(f):
    d=pd.read_excel(os.path.join(SRC,f),dtype=str); d.columns=['pc','place','sub','main','prov']; return d
bnl=rb('zipcodes_num_nl_2025.xls'); bfr=rb('zipcodes_num_fr_2025.xls')
assert len(bnl)==len(bfr) and (bnl.pc.values==bfr.pc.values).all()
diff=(bnl.place!=bfr.place).sum()
LOG['sources'].append(f'bpost NL ve FR listelerinde yer adları birebir aynı ({diff} fark): bpost her yeri yalnızca yerel dilde veriyor.')
special=bnl[bnl.prov.isna()]; geo=bnl[bnl.prov.notna()].copy()
for _,x in special.iterrows():
    LOG['excluded'].append(f'{x.pc} {x.place}: bpost listesinde il/deelgemeente bilgisi yok (kuruma/özel servise ayrılmış kod)')

# ---------- BeSt ----------
best=pd.read_csv(os.path.expanduser('~/work/best_agg.csv'),dtype=str).fillna('')
best['n']=best.n.astype(float); bc=best[best.status=='current']
cand=bc.groupby(['postcode','municipality_id']).n.sum().reset_index()
cand_of={pc:dict(zip(g.municipality_id,g.n)) for pc,g in cand.groupby('postcode')}
for pc in sorted(set(special.pc)&set(best.postcode)):
    LOG['excluded_note'].append(f'{pc}: özel kod olmasına rağmen BeSt\'te {int(best[best.postcode==pc].n.sum())} adres var (belediye {",".join(sorted(set(best[best.postcode==pc].municipality_id)))}); yine de hariç tutuldu')
# Brussels fr postal names (BeSt postalinfo via postalstreets files)
bru_fr={}
for f in ['postalstreets-latest/Brussels_postal_street.csv','postalstreets-empty-latest/Brussels_empty_street.csv']:
    d=pd.read_csv(os.path.join(BASE,f),dtype=str).fillna('')
    for _,x in d[(d.postal_nl!='')&(d.postal_fr!='')].drop_duplicates(['postal_id','postal_nl','postal_fr']).iterrows():
        bru_fr[(x.postal_id,x.postal_nl)]=x.postal_fr

def norm(s):
    s=unicodedata.normalize('NFKD',str(s)).encode('ascii','ignore').decode().upper()
    s=re.sub(r'\s*\(.*?\)','',s); return re.sub(r'[^A-Z]','',s)
name_idx=collections.defaultdict(set)
for _,x in cur[cur.LVL_REFNIS=='4'].iterrows():
    for c in ['TX_REFNIS_NL','TX_REFNIS_FR','TX_REFNIS_DE']: name_idx[norm(x[c])].add(x.CD_REFNIS)

def resolve(pc,main):
    cands=cand_of.get(pc,{})
    by_name=name_idx.get(norm(main),set())
    inter=by_name&set(cands) if cands else by_name
    if len(inter)==1: return next(iter(inter)),None
    if len(by_name)==1 and not cands: return next(iter(by_name)),f'{pc}: BeSt\'te bu koda adres yok; belediye yalnızca bpost hoofdgemeente adından ({main}) eşlendi'
    if len(cands)==1:
        m=next(iter(cands))
        note=None if by_name=={m} else f'{pc}: bpost hoofdgemeente "{main}" REFNIS adıyla tam eşleşmedi{" (aday: "+",".join(sorted(by_name))+")" if by_name else ""}; BeSt\'teki tek belediye {m} ({areas["BE-MUN-"+m]["names"].get("nl") or areas["BE-MUN-"+m]["names"].get("fr")}) alındı'
        return m,note
    return None,f'{pc}: "{main}" çözülemedi; ad adayları {sorted(by_name)}, BeSt adayları {sorted(cands)}'

pc_rows=collections.OrderedDict()
for i,x in geo.iterrows(): pc_rows.setdefault(x.pc,[]).append(x)
for pc,rows in pc_rows.items():
    if not re.fullmatch(r'\d{4}',pc): LOG['validation'].append(f'Geçersiz posta kodu biçimi: {pc}'); continue
    place_muni=[]; places=[]
    for x in rows:
        m,note=resolve(pc,x.main)
        if note and note not in LOG['ambiguous']: LOG['ambiguous'].append(note)
        place_muni.append(m)
        langs=muni_lang.get(m,['nl'])
        if m and m.startswith('21') or (m is None and pc<'1300' and pc>='1000'):
            p={'nl':x.place}
            fr=bru_fr.get((pc,x.place))
            if not fr and m:
                mn=areas['BE-MUN-'+m]['names']
                if norm(mn.get('nl',''))==norm(x.place): fr=mn.get('fr')
            if fr: p['fr']=fr
            else: LOG['ambiguous'].append(f'{pc} {x.place}: Brüksel yeri için resmi kaynakta Fransızca yer adı bulunamadı; places\'e yalnızca nl yazıldı')
        elif m in GERMAN: p={'de':x.place}
        elif langs==['fr']: p={'fr':x.place}
        else: p={'nl':x.place}
        places.append(p)
    counts=collections.Counter(m for m in place_muni if m)
    if not counts: LOG['validation'].append(f'{pc}: geçerli belediye bulunamadı, listeye alınmadı'); continue
    best_n=max(counts.values()); winner=next(m for m in place_muni if m and counts[m]==best_n)
    bcands=cand_of.get(pc,{})
    if len(counts)>1:
        LOG['multi'].append(f'{pc}: yerler → '+'; '.join(f'{m} {areas["BE-MUN-"+m]["names"].get("nl") or areas["BE-MUN-"+m]["names"].get("fr")} ({counts[m]} yer)' for m in counts)+f' ⇒ parent BE-MUN-{winner}'+(' (eşitlik: bpost\'taki ilk kayıt)' if list(counts.values()).count(best_n)>1 else ''))
    extra={m:n for m,n in bcands.items() if m not in counts}
    if extra:
        LOG['best_span'].append(f'{pc} → BE-MUN-{winner}; BeSt\'te başka belediyelerde de adres var: '+', '.join(f'{m} ({int(n)} adres)' for m,n in sorted(extra.items()))+f' / toplam {int(sum(bcands.values()))}')
    langs=muni_lang[winner]
    add(f'BE-PC-{pc}','postal_code',f'BE-MUN-{winner}',{lg:pc for lg in langs},places)

# ---------- report meta ----------
LOG['source_lines']=[
 'Statbel REFNIS – sayfa: https://statbel.fgov.be/en/open-data/code-refnis-0',
 '   dosya: https://statbel.fgov.be/sites/default/files/files/opendata/REFNIS%20code/TU_COM_REFNIS-20250101.xlsx (TU_COM_REFNIS-20250101.xlsx, 146 190 bayt)',
 '   yapı tarihi 01.01.2025 (sayfadaki en güncel sürüm), sunucu Last-Modified 28.11.2024. Sadece DT_VLDT_END = 31/12/9999 olan satırlar alındı.',
 'bpost posta kodu listesi – sayfa: https://www.bpost.be/nl/postcodevalidatie-tool (FR: /fr/outil-de-validation-de-codes-postaux)',
 '   dosyalar: https://www.bpost.be/sites/default/files/zipcodes/zipcodes_num_nl_2025.xls ve zipcodes_num_fr_2025.xls (her biri 328 192 bayt, 2764 satır)',
 '   sunucu Last-Modified 16.03.2026. Almanca (de) liste bpost\'ta yok (zipcodes_num_de_*.xls → 404).',
 'Posta kodu → belediye eşlemesi: BeSt Address / OpenAddress CSV (FOD BOSA) – https://opendata.bosa.be/index.nl.html',
 '   dosyalar: openaddress-bevlg.zip, openaddress-bebru.zip, openaddress-bewal.zip, postalstreets-latest.zip, postalstreets-empty-latest.zip',
 '   sunucu Last-Modified 30.09.2026 (haftalık güncelleme). Yalnızca status=current adresler (6 654 225 adres) sayıldı.',
 'ISO 3166-2:BE – https://www.iso.org/obp/ui/#iso:code:3166:BE. OBP sayfası kullanım koşullarını kabul etmeyi istediği için açılmadı; kodlar',
 '   (BE-VLG/WAL/BRU; BE-VAN/VBR/VLI/VOV/VWV/WBR/WHT/WLG/WLX/WNA) standardın bilinen listesinden yazıldı – bkz. Belirsizlikler.',
 'Çapraz kontrol için Wikipedia/üçüncü taraf listeleri kullanılmadı.']
LOG['decisions']=[
 'İl ve arrondissement adlarında "Provincie/Province de/Provinz" ve "Arrondissement/Bezirk" önekleri atıldı (örn. "Provincie Limburg" → "Limburg"); bölge adları Statbel\'deki tam haliyle bırakıldı.',
 'Belediye adları Statbel\'deki gibi aynen kullanıldı; REFNIS\'in eşsesli adlar için eklediği ayraç ekleri korundu (örn. "Tielt (Tielt)", BE-MUN-37022). İstenirse uygulamada gösterirken ayraç kısmı atılabilir.',
 'Statbel nl/fr/de adlarının üçünü de her idari satıra ekledi (bölüm 3: "Statbel\'in verdiği diğer diller").',
 'en adları Statbel\'de yok; yalnızca yerleşik İngilizce adı nl/fr/de adlarının hepsinden farklı olanlara eklendi: '+', '.join(f"{c}={areas[c]['names']['en']}" for c in sorted(areas) if 'en' in areas[c]['names'])+'. (Bruges = fr adıyla aynı olduğu için eklenmedi.)',
 'Almanca dil bölgesi = 9 belediye (63001 Amel, 63012 Büllingen, 63013 Bütgenbach, 63023 Eupen, 63040 Kelmis, 63048 Lontzen, 63061 Raeren, 63067 Sankt Vith, 63087 Burg-Reuland). Bu bölgedeki posta kodlarının names değeri fr+de, places dili de.',
 'bpost yer adlarını tek dilde (yerel dil) veriyor; places dili belediyenin bölgesine göre etiketlendi: Flaman bölgesi nl, Wallonya fr, Almanca bölge de, Brüksel nl (+fr: BeSt postalinfo ya da yer = belediye ise Statbel fr adı).',
 'Posta kodu parent\'ı: her bpost yeri, bpost\'un "Hoofdgemeente" alanının REFNIS adıyla (BeSt\'teki aday belediyelerle kesiştirilerek) eşlenmesiyle belediyeye bağlandı; en çok yeri olan belediye parent oldu.',
 'Hasselt 1.1.2025 birleşmesiyle yeni NIS kodu aldı: BE-MUN-71072 (eski 71022 artık geçersiz). Görev tanımındaki BE-MUN-71022 örneği eski koddur.',
 'bpost\'ta olup BeSt\'te hiç adresi olmayan 8 coğrafi kod listeye alındı (3668, 3941, 4784, 4791, 6642, 6688, 6704, 6706); belediyeleri bpost hoofdgemeente adından eşlendi.']
LOG['uncertain']=[
 'ISO 3166-2:BE kodları resmi ISO OBP\'de bu çalıştırmada doğrulanamadı (koşul onayı gerekiyordu). Kodlar 2008\'den beri değişmedi ama resmi teyit açık.',
 'Almanca bölgedeki yerlerin Fransızca adları (örn. Kelmis/La Calamine yer düzeyinde) bpost\'ta yok; places\'e yalnızca de yazıldı. Wallonya\'daki yerlerin nl adları ve Flandre\'deki yerlerin fr adları da eklenmedi.',
 'BeSt dosyalarının yerel kopyası 30.09.2026 08:42 tarihli; BOSA sunucusundaki zip\'ler 30.09.2026 10:42 GMT tarihli. Aynı haftalık yayın olduğu varsayıldı.']
# ---------- output ----------
ORDER=['country','region','province','arrondissement','municipality','postal_code']
lst=sorted(areas.values(),key=lambda a:(ORDER.index(a['level']),a['code']))
src=f"bpost zipcodes_num_nl/fr_2025.xls (Last-Modified 2026-03-16); Statbel REFNIS TU_COM_REFNIS-20250101 (Last-Modified 2024-11-28); BeSt Address OpenAddress CSV (BOSA, 2026-09-30)"
doc={'version':VERSION,'source':src,'areas':lst}
json.dump(doc,open(os.path.join(OUT,'areas.json'),'w',encoding='utf-8'),ensure_ascii=False,indent=1)
json.dump(dict(LOG),open(os.path.join(OUT,'_log.json'),'w',encoding='utf-8'),ensure_ascii=False,indent=1)
print({k:len(v) for k,v in LOG.items()}); print(collections.Counter(a['level'] for a in lst))
