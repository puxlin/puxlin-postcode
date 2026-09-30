#!/usr/bin/env python3
"""Usage: build_nl.py <version> <outdir> <pc6hnr csv> <gem_2026.csv>  -> areas_nl_proposal.json + rapor_nl.txt"""
import pandas as pd, json, os, sys, collections
BASE=os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
VERSION,OUT,PC6,GEMCSV=sys.argv[1:5]
g=pd.read_excel(os.path.join(BASE,'sources','gemeenten-alfabetisch-2026.xlsx'),sheet_name='Gemeenten_alfabetisch',dtype=str)
ISO={'Groningen':'NL-GR','Fryslân':'NL-FR','Drenthe':'NL-DR','Overijssel':'NL-OV','Flevoland':'NL-FL','Gelderland':'NL-GE',
     'Utrecht':'NL-UT','Noord-Holland':'NL-NH','Zuid-Holland':'NL-ZH','Zeeland':'NL-ZE','Noord-Brabant':'NL-NB','Limburg':'NL-LI'}
R=[]; w=R.append
areas={}
areas['NL']={'code':'NL','level':'country','parent':None,'names':{'nl':'Nederland','en':'Netherlands'}}
for _,p in g.drop_duplicates('ProvinciecodePV').iterrows():
    c=ISO[p.Provincienaam]; n={'nl':p.Provincienaam}
    if c=='NL-FR': n['fy']=p.Provincienaam
    areas[c]={'code':c,'level':'province','parent':'NL','names':n}
for _,x in g.iterrows():
    c='NL-MUN-'+x.GemeentecodeGM
    areas[c]={'code':c,'level':'municipality','parent':ISO[x.Provincienaam],'names':{'nl':x.Gemeentenaam}}
gem_codes=set(g.Gemeentecode)
gc=pd.read_csv(GEMCSV,sep=';',dtype=str,encoding='utf-8-sig')
xg=set(gc.Gemeente2026)^gem_codes
if xg: w(f'! CBS gemeentelijst ile pc6hnr gem_2026.csv farklı: {sorted(xg)} ('+'; '.join(gc[gc.Gemeente2026.isin(xg)].Gemeentenaam2026)+') – pc6hnr\'de bu koda düşen adres yok, göz ardı edildi')
d=pd.read_csv(PC6,sep=';',dtype=str,usecols=['PC6','Gemeente2026'])
d['pc4']=d.PC6.str[:4]
cnt=d.groupby(['pc4','Gemeente2026']).size().reset_index(name='n')
split=0; ties=[]; splits=[]; unknown=set(cnt.Gemeente2026)-gem_codes
for pc4,grp in cnt.groupby('pc4'):
    grp=grp.sort_values(['n','Gemeente2026'],ascending=[False,True])
    top=grp.iloc[0]
    if len(grp)>1:
        split+=1; splits.append(f'{pc4}: '+', '.join(f'GM{a} ({b})' for a,b in zip(grp.Gemeente2026,grp.n))+f' → NL-MUN-GM{top.Gemeente2026}')
        if grp.iloc[1].n==top.n: ties.append(f'{pc4}: eşit adres sayısı {list(zip(grp.Gemeente2026,grp.n))} → en küçük gemeentecode seçildi')
    c='NL-PC-'+pc4
    areas[c]={'code':c,'level':'postal_code','parent':'NL-MUN-GM'+top.Gemeente2026,'names':{'nl':pc4},'places':[]}
# places: NL kaynağında PC4 için yer adı yok -> boş liste yerine gemeente adı kullanılmaz; anahtar boş bırakılır
ORDER=['country','region','province','arrondissement','municipality','postal_code']
lst=sorted(areas.values(),key=lambda a:(ORDER.index(a['level']),a['code']))
mun_with=set(a['parent'] for a in lst if a['level']=='postal_code')
nopc=[a['code']+' '+a['names']['nl'] for a in lst if a['level']=='municipality' and a['code'] not in mun_with]
doc={'version':VERSION,'status':'PROPOSAL – ana listeyle birleştirilmez; kodlar henüz kararlaştırılmadı',
     'source':'CBS Gemeentelijke indeling op 1 januari 2026 (gemeenten-alfabetisch-2026.xlsx); CBS Buurt, wijk en gemeente 2026 voor postcode huisnummer (pc6hnr20260801_gwb, peildatum 2026-08-01)','areas':lst}
json.dump(doc,open(os.path.join(OUT,'areas_nl_proposal.json'),'w',encoding='utf-8'),ensure_ascii=False,indent=1)
c=collections.Counter(a['level'] for a in lst)
H=['HOLLANDA ÖNERİ DOSYASI RAPORU (areas_nl_proposal.json) – ÖNERİDİR, ana listeye girmez',
 'Kaynaklar:',
 ' - CBS Gemeentelijke indeling op 1 januari 2026: https://www.cbs.nl/nl-nl/onze-diensten/methoden/classificaties/overig/gemeentelijke-indelingen-per-jaar/indeling-per-jaar/gemeentelijke-indeling-op-1-januari-2026',
 '   dosya: https://www.cbs.nl/-/media/cbs/onze-diensten/methoden/classificaties/overig/gemeenten-alfabetisch-2026.xlsx (Last-Modified 06.01.2026)',
 ' - CBS Buurt, wijk en gemeente 2026 voor postcode huisnummer (yayın 18.09.2026): https://www.cbs.nl/nl-nl/maatwerk/2026/38/buurt-wijk-en-gemeente-2026-voor-postcode-huisnummer',
 '   dosya: https://download.cbs.nl/postcode/pc6hnr20260801_gwb.zip (Last-Modified 18.09.2026; BAG peildatum 01.08.2026)',
 f'Satır sayıları: country {c["country"]}, province {c["province"]}, municipality {c["municipality"]} (CBS: 342), postal_code (PC4) {c["postal_code"]}',
 f'PC4 → gemeente: her PC4 için adres (postcode+huisnummer) sayısı en yüksek gemeente parent yapıldı. Birden fazla gemeenteye yayılan PC4: {split}.',
 'Birden fazla gemeenteye yayılan PC4\'ler (adres sayısı):']+[' - '+t for t in splits]+['Eşitlikler:']+([' - '+t for t in ties] or [' - yok'])+[
 f'PC4\'ü olmayan gemeente: {nopc or "yok"}',
 f'CBS listesinde olmayan gemeentecode (pc6hnr): {sorted(unknown) or "yok"}',
 'Belirsizlikler / notlar:',
 ' - PC4 için resmi yer adı (woonplaats) bu kaynaklarda yok; places boş liste olarak bırakıldı. İstenirse BAG woonplaatsen (PDOK) ile doldurulabilir.',
 ' - Frysk (fy) isimler: CBS tek resmi ad veriyor. Yalnızca il "Fryslân" için fy eklendi; Frizce resmi adlı gemeenten (örn. Súdwest-Fryslân, Tytsjerksteradiel) CBS adıyla nl etiketinde; ayrı fy adları (örn. Leeuwarden/Ljouwert) resmi kaynaktan alınamadığı için eklenmedi.',
 ' - İl ISO kodları (NL-GR … NL-LI) CBS il adından eşlendi; ISO OBP\'de doğrulanmadı.',
 ' - Belçika\'daki gibi özel/kurumsal kod ayıklaması yapılmadı: pc6hnr yalnızca BAG\'daki adreslere verilmiş kodları içerir (postbus kodları zaten yok).']
open(os.path.join(OUT,'rapor_nl.txt'),'w',encoding='utf-8').write('\n'.join(H+R)+'\n')
print('\n'.join(H+R))
