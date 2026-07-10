#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import zipfile
import re

z = zipfile.ZipFile(r'大论文初稿\plate_fin_heat_exchanger.mph')
content = z.read('dmodel.xml').decode('utf-8', errors='ignore')

print('=== Parameters ===')
params = re.findall(r'<parameter[^>]*name="([^"]+)"[^>]*expr="([^"]*)"', content)
for n, e in params[:20]:
    print(f'{n} = {e}')

print('\n=== Materials ===')
mats = re.findall(r'<material[^>]*tag="([^"]+)"[^>]*label="([^"]*)"', content)
for t, l in mats:
    print(f'{t}: {l}')

print('\n=== Physics ===')
phys = re.findall(r'<physics[^>]*tag="([^"]+)"[^>]*interface="([^"]+)"', content)
for t, i in phys:
    print(f'{t}: {i}')

print('\n=== Study Steps ===')
studies = re.findall(r'<studyStep[^>]*type="([^"]+)"[^>]*label="([^"]*)"', content)
for t, l in studies:
    print(f'{t}: {l}')
