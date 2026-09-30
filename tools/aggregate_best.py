#!/usr/bin/env python3
"""BeSt OpenAddress CSV'lerini (postcode, municipality_id, status, adlar) bazında sayar -> ~/work/best_agg.csv
Usage: aggregate_best.py <klasör: openaddress-bevlg/bebru/bewal.csv>"""
import pandas as pd, os, sys
D=sys.argv[1]; cols=['municipality_id','postcode','status','municipality_name_nl','municipality_name_fr','municipality_name_de','postname_nl','postname_fr']
out=[]
for r in ['bebru','bewal','bevlg']:
    agg=None
    for ch in pd.read_csv(os.path.join(D,f'openaddress-{r}.csv'),usecols=cols,dtype=str,chunksize=1000000):
        g=ch.fillna('').groupby(cols).size()
        agg=g if agg is None else agg.add(g,fill_value=0)
    a=agg.reset_index(name='n'); a['region']=r; out.append(a)
os.makedirs(os.path.expanduser('~/work'),exist_ok=True)
pd.concat(out).to_csv(os.path.expanduser('~/work/best_agg.csv'),index=False)
