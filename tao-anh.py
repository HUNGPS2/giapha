#!/usr/bin/env python3
"""
tao-anh.py — Chuan bi cho viec them anh chan dung.

Chay:  python tao-anh.py

Sinh ra:
  anh/                — thu muc de bo anh vao
  anh/DANH-SACH.txt   — danh sach TEN FILE can dat cho tung nguoi
  anh.json            — trang doc file nay de biet ai co anh

CACH DUNG:
  1. Chay script -> mo anh/DANH-SACH.txt
  2. Tai anh tu MyHeritage (chuot phai -> Save image as)
  3. Doi ten theo DANH-SACH.txt, bo vao thu muc anh/
  4. Chay lai script -> no quet thu muc, cap nhat anh.json
  5. Upload anh/ va anh.json len GitHub

THAY ANH SAU NAY: chi can tha file moi de len file cu, upload lai.
Khong phai chay lai gi ca.
"""
import json
import os
import re
import sys
import unicodedata
from collections import Counter

DATA = sys.argv[1] if len(sys.argv) > 1 else 'data.json'
THU_MUC = 'anh'
DUOI_ANH = ('.jpg', '.jpeg', '.png', '.webp')


def slug(s):
    """'PHẠM ĐÌNH QUỲNH' -> 'pham-dinh-quynh'"""
    s = s.replace('Đ', 'D').replace('đ', 'd')
    s = unicodedata.normalize('NFD', s)
    s = ''.join(c for c in s if unicodedata.category(c) != 'Mn')
    s = re.sub(r'[^a-zA-Z0-9]+', '-', s).strip('-').lower()
    return s


def main():
    if not os.path.exists(DATA):
        print(f'Khong thay {DATA}. Chay capnhat.bat truoc.')
        sys.exit(1)

    d = json.load(open(DATA, encoding='utf-8'))
    P = d['nguoi']

    # Sinh ten file. Neu TRUNG ten -> them doi de phan biet.
    dem = Counter(slug(p['ten']) for p in P.values())
    ten_file = {}
    for pid, p in P.items():
        s = slug(p['ten'])
        if dem[s] > 1:
            s = f'{s}-doi-{p["doi"]}'      # 'pham-dinh-huy-doi-13'
        ten_file[pid] = s

    os.makedirs(THU_MUC, exist_ok=True)

    # Quet thu muc anh/. Hai loai anh, TACH BACH:
    #
    #   CHAN DUNG:  pham-dinh-quynh.jpg      (anh chinh)
    #               pham-dinh-quynh-2.jpg    (anh phu: luc tre, luc ve gia)
    #
    #   TU LIEU  :  pham-dinh-quynh-tl1.jpg  (bia mo, sac phong, nha tho ho)
    #               pham-dinh-quynh-tl2.jpg
    #
    # Chu thich cho anh tu lieu go trong Note cua Gramps: '[tl1] Bia Pha ky...'
    #
    # QUAN TRONG: anh CHINH (khong co so) phai dung DAU.
    # Sap thuong thi 'pham-sy-hung-2.jpg' < 'pham-sy-hung.jpg'
    # (dau '-' xep truoc dau '.') -> anh phu thanh anh chinh. Sai.
    tam = {}          # chan dung
    tam_tl = {}       # tu lieu
    for f in os.listdir(THU_MUC):
        goc, duoi = os.path.splitext(f)
        if duoi.lower() not in DUOI_ANH:
            continue

        # Thu khop TU LIEU truoc: '<ten>-tl<N>'
        m_tl = re.fullmatch(r'(.+?)-tl(\d+)', goc, re.I)
        if m_tl:
            base, so = m_tl.group(1), int(m_tl.group(2))
            for pid, tf in ten_file.items():
                if base == tf:
                    tam_tl.setdefault(pid, []).append((so, f))
                    break
            continue

        # Con lai la CHAN DUNG: '<ten>' hoac '<ten>-<N>'
        m = re.fullmatch(r'(.+?)(?:-(\d+))?', goc)
        base = m.group(1)
        so = int(m.group(2)) if m.group(2) else 0
        for pid, tf in ten_file.items():
            if base == tf:
                tam.setdefault(pid, []).append((so, f))
                break

    co_anh = {pid: [f for _, f in sorted(ds)]      # sap theo SO, anh chinh (0) truoc
              for pid, ds in tam.items()}
    co_tl = {pid: [{'f': f, 'so': so} for so, f in sorted(ds)]
             for pid, ds in tam_tl.items()}

    # Ghi anh.json cho trang doc.
    # Hai muc rieng: chan dung va tu lieu -> trang khong lan lon.
    with open('anh.json', 'w', encoding='utf-8') as fo:
        json.dump({'chan_dung': co_anh, 'tu_lieu': co_tl},
                  fo, ensure_ascii=False, separators=(',', ':'))

    # Ghi danh sach ten file
    ds = os.path.join(THU_MUC, 'DANH-SACH.txt')
    with open(ds, 'w', encoding='utf-8') as fo:
        fo.write('DANH SACH TEN FILE ANH\n')
        fo.write('=' * 60 + '\n\n')
        fo.write('Tai anh tu MyHeritage, doi ten theo cot ben phai,\n')
        fo.write('roi bo vao thu muc anh/ nay.\n\n')
        fo.write('Nguoi co NHIEU ANH: them so vao cuoi\n')
        fo.write('   pham-dinh-quynh.jpg     <- anh chinh (hien tren the)\n')
        fo.write('   pham-dinh-quynh-2.jpg   <- anh phu\n')
        fo.write('   pham-dinh-quynh-3.jpg\n\n')
        fo.write('=' * 60 + '\n\n')

        # Xep theo doi cho de tim
        for doi in sorted({p['doi'] for p in P.values()}):
            ds_doi = sorted(
                [p for p in P.values() if p['doi'] == doi],
                key=lambda x: (x.get('khoa_sap', []), x['ten'])
            )
            fo.write(f'\n--- DOI {doi} ---\n')
            for p in ds_doi:
                tf = ten_file[p['id']]
                dau = '[co anh]' if p['id'] in co_anh else '[      ]'
                fo.write(f'{dau}  {p["ten"]:<32} {tf}.jpg\n')

    # Bao cao
    tong_anh = sum(len(v) for v in co_anh.values())
    tong_tl = sum(len(v) for v in co_tl.values())
    print(f'Tong: {len(P)} nguoi')
    print(f'Chan dung: {len(co_anh)} nguoi ({tong_anh} anh)')
    print(f'Tu lieu  : {len(co_tl)} nguoi ({tong_tl} anh)')
    print(f'Chua co anh: {len(P) - len(co_anh)} nguoi')

    # Bao anh tu lieu CHUA CO CHU THICH trong Note
    thieu_ct = []
    for pid, ds_tl in co_tl.items():
        ct = P[pid].get('ct_anh') or {}
        for a in ds_tl:
            if str(a['so']) not in ct and a['so'] not in ct:
                thieu_ct.append((P[pid]['ten'], a['f'], a['so']))
    if thieu_ct:
        print()
        print('ANH TU LIEU CHUA CO CHU THICH:')
        print('  (go vao Note cua nguoi do trong Gramps, vd: [tl1] Bia Pha ky ho Pham)')
        for ten, f, so in thieu_ct[:10]:
            print(f'  {ten[:24]:<26} {f:<28} thieu [tl{so}]')
    print()
    print(f'Danh sach ten file: {ds}')
    print(f'Ghi ra: anh.json')

    # Canh bao file thua trong thu muc anh/
    thua = []
    for f in os.listdir(THU_MUC):
        goc, duoi = os.path.splitext(f)
        if duoi.lower() not in DUOI_ANH:
            continue
        m_tl = re.fullmatch(r'(.+?)-tl\d+', goc, re.I)
        base = m_tl.group(1) if m_tl else re.fullmatch(r'(.+?)(?:-\d+)?', goc).group(1)
        if base not in ten_file.values():
            thua.append(f)
    if thua:
        print()
        print('CANH BAO — file trong anh/ khong khop voi ai:')
        for f in thua[:10]:
            print(f'  {f}')
        print('  (kiem tra lai ten file trong DANH-SACH.txt)')


if __name__ == '__main__':
    main()
