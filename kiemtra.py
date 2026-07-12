#!/usr/bin/env python3
"""
kiemtra.py — Kiem tra an toan truoc khi day len GitHub.

Chan viec push neu phat hien bat ky ro ri nao:
  - Nguoi con song bi lo ngay/thang sinh
  - Email hoac dia chi trong file
  - Link anh MyHeritage
  - File hong

Tra ve ma 0 = sach, 1 = co van de (script goi se dung lai).
Dung chung cho ca capnhat.sh (Linux/Mac) va capnhat.bat (Windows).
"""
import json
import re
import sys

RE_EMAIL = re.compile(r'[\w.+-]+@[\w-]+\.[\w.]+')

loi = []


def kiem_json():
    try:
        d = json.load(open('data.json', encoding='utf-8'))
    except Exception as e:
        loi.append(f'data.json hong hoac khong doc duoc: {e}')
        return None

    P = d.get('nguoi')
    if not P:
        loi.append('data.json rong — khong co nguoi nao')
        return None

    # Nguoi CON SONG khong duoc co ngay/thang sinh, chi duoc co NAM
    lo = [p['ten'] for p in P.values()
          if p.get('con_song') and p.get('sinh')
          and not re.fullmatch(r'\d{4}', str(p['sinh']))]
    if lo:
        loi.append(f'{len(lo)} nguoi con song bi lo ngay/thang sinh: {", ".join(lo[:3])}')

    raw = open('data.json', encoding='utf-8').read()
    if RE_EMAIL.search(raw):
        loi.append('data.json chua email')
    if 'mhcache' in raw or 'myheritage' in raw.lower():
        loi.append('data.json chua link anh / dinh danh MyHeritage')

    return P


def kiem_gedcom():
    try:
        g = open('giapha.ged', encoding='utf-8').read()
    except Exception as e:
        loi.append(f'giapha.ged khong doc duoc: {e}')
        return

    if RE_EMAIL.search(g):
        loi.append('giapha.ged chua email')
    if 'mhcache' in g:
        loi.append('giapha.ged chua link anh MyHeritage')
    if 'DATE ...' in g:
        loi.append('giapha.ged con dong "DATE ..." vo nghia')

    # Nguoi con song trong GEDCOM: khong duoc co DEAT, BIRT chi duoc co NAM
    for rec in re.split(r'\n(?=0 @)', g):
        dong_dau = rec.split('\n')[0]
        if ' INDI' not in dong_dau:
            continue
        if re.search(r'^1 DEAT', rec, re.M):
            continue                      # da mat -> duoc phep co ngay/thang
        bm = re.search(r'^1 BIRT\n^2 DATE (.+)$', rec, re.M)
        if bm and not re.fullmatch(r'\d{4}', bm.group(1).strip()):
            nm = re.search(r'^1 NAME (.+)$', rec, re.M)
            ten = nm.group(1)[:26] if nm else '?'
            loi.append(f'giapha.ged: nguoi con song lo ngay/thang — {ten}')
            break


def main():
    P = kiem_json()
    kiem_gedcom()

    if loi:
        for x in loi:
            print(f'   [X] {x}')
        sys.exit(1)

    song = sum(1 for p in P.values() if p.get('con_song'))
    mat = len(P) - song
    print(f'   [OK] Rieng tu: {song} nguoi con song, khong ai lo ngay/thang')
    print(f'   [OK] Khong co email, dia chi, hay link anh trong ca hai file')
    print(f'   [OK] Tong {len(P)} nguoi ({song} con song, {mat} da mat)')
    sys.exit(0)


if __name__ == '__main__':
    main()
