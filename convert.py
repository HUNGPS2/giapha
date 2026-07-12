#!/usr/bin/env python3
"""
Chuyen GEDCOM (xuat tu MyHeritage) sang JSON cho trang gia pha.
Xu ly rieng cho du lieu tieng Viet:
  - Bo co DEAT Y gia (MyHeritage gan cho ca nguoi song)
  - Chuan hoa ten (4 kieu viet khac nhau)
  - Sinh khoa tim kiem khong dau
  - Tinh doi (generation) tu thuy to
"""
import re, json, unicodedata, sys
from collections import defaultdict

SRC = sys.argv[1] if len(sys.argv) > 1 else '/mnt/user-data/uploads/f0i518_6108819c2moc6q0af58z91_A.ged'
OUT = sys.argv[2] if len(sys.argv) > 2 else '/home/claude/site/data.json'


def bo_dau(s):
    """Bo dau tieng Viet -> chuoi khong dau, chu thuong. Dung cho tim kiem."""
    s = s.replace('Đ', 'D').replace('đ', 'd')
    s = unicodedata.normalize('NFD', s)
    s = ''.join(c for c in s if unicodedata.category(c) != 'Mn')
    return s.lower()


def chuan_hoa_ten(raw):
    """
    GEDCOM co 4 kieu:
      'PHẠM SỸ HÙNG //'      -> ho trong, ten day du o GIVN
      'THỊ CÁT /NGUYỄN/'     -> ho trong dau /
      '2. PHẠM ĐÌNH ĐỘ //'   -> lan so thu tu
      'Phạm Thu Na //'       -> chu thuong
    Tra ve ten day du, da bo so thu tu, giu nguyen dau va hoa/thuong goc.
    """
    raw = raw.strip()
    m = re.match(r'^(.*?)/(.*?)/(.*)$', raw)
    if m:
        truoc, ho, sau = m.group(1).strip(), m.group(2).strip(), m.group(3).strip()
        if ho:
            # kieu 'THỊ CÁT /NGUYỄN/' -> ho dat len truoc
            ten = f'{ho} {truoc}'.strip()
        else:
            ten = f'{truoc} {sau}'.strip()
    else:
        ten = raw
    # bo so thu tu dau ten: '2. ', '12.', '3 -'
    ten = re.sub(r'^\s*\d+\s*[.\-)]\s*', '', ten)
    ten = re.sub(r'\s+', ' ', ten).strip()
    return ten


def doc_gedcom(path):
    txt = open(path, encoding='utf-8-sig').read().replace('\r\n', '\n')
    lines = txt.split('\n')
    records = []
    cur = None
    for ln in lines:
        if not ln.strip():
            continue
        m = re.match(r'^(\d+) (.*)$', ln)
        if not m:
            continue
        lvl, rest = int(m.group(1)), m.group(2)
        if lvl == 0:
            cur = {'raw': [], 'head': rest}
            records.append(cur)
        elif cur is not None:
            cur['raw'].append((lvl, rest))
    return records


def parse():
    recs = doc_gedcom(SRC)
    people, fams = {}, {}

    for r in recs:
        head = r['head']
        mi = re.match(r'^@(I[^@]+)@ INDI$', head)
        mf = re.match(r'^@(F[^@]+)@ FAM$', head)

        if mi:
            pid = mi.group(1)
            p = {'id': pid, 'ten': '', 'gioi': '', 'sinh': '', 'mat': '',
                 'noi_sinh': '', 'fams': [], 'famc': None, 'anh': []}
            i = 0
            raw = r['raw']
            while i < len(raw):
                lvl, val = raw[i]
                if lvl == 1:
                    tag = val.split(' ', 1)[0]
                    arg = val[len(tag):].strip()

                    if tag == 'NAME':
                        p['ten'] = chuan_hoa_ten(arg)
                    elif tag == 'SEX':
                        p['gioi'] = arg
                    elif tag == 'FAMS':
                        p['fams'].append(arg.strip('@'))
                    elif tag == 'FAMC':
                        p['famc'] = arg.strip('@')
                    elif tag in ('BIRT', 'DEAT'):
                        # doc cac dong con (level 2)
                        j = i + 1
                        date, plac = '', ''
                        while j < len(raw) and raw[j][0] > 1:
                            sub = raw[j][1]
                            if sub.startswith('DATE '):
                                date = sub[5:].strip()
                            elif sub.startswith('PLAC '):
                                plac = sub[5:].strip()
                            j += 1
                        # QUAN TRONG: MyHeritage ghi 'DEAT Y' + 'DATE ...' cho ca nguoi song
                        if date == '...' or date == '':
                            date = ''
                        if tag == 'BIRT':
                            p['sinh'] = date
                            p['noi_sinh'] = plac
                        else:
                            p['mat'] = date  # rong = con song / khong ro
                        i = j - 1
                    elif tag == 'OBJE':
                        j = i + 1
                        file_, titl = '', ''
                        while j < len(raw) and raw[j][0] > 1:
                            sub = raw[j][1]
                            if sub.startswith('FILE '):
                                file_ = sub[5:].strip()
                            elif sub.startswith('TITL '):
                                titl = sub[5:].strip()
                            j += 1
                        if file_:
                            p['anh'].append({'url': file_, 'titl': titl})
                        i = j - 1
                i += 1
            people[pid] = p

        elif mf:
            fid = mf.group(1)
            f = {'id': fid, 'chong': None, 'vo': None, 'con': [], 'cuoi': ''}
            raw = r['raw']
            i = 0
            while i < len(raw):
                lvl, val = raw[i]
                if lvl == 1:
                    tag = val.split(' ', 1)[0]
                    arg = val[len(tag):].strip()
                    if tag == 'HUSB':
                        f['chong'] = arg.strip('@')
                    elif tag == 'WIFE':
                        f['vo'] = arg.strip('@')
                    elif tag == 'CHIL':
                        f['con'].append(arg.strip('@'))
                    elif tag == 'MARR':
                        j = i + 1
                        while j < len(raw) and raw[j][0] > 1:
                            if raw[j][1].startswith('DATE '):
                                f['cuoi'] = raw[j][1][5:].strip()
                            j += 1
                        i = j - 1
                i += 1
            fams[fid] = f

    return people, fams


def tinh_doi(people, fams):
    """
    Tinh doi theo LOGIC GIA PHA VIET:
      - Nguoi co cha me trong cay = huyet thong -> tinh doi tu thuy to xuong
      - Nguoi KHONG co cha me nhung co vo/chong = dau/re -> lay doi theo vo/chong
      - Thuy to that = nguoi khong cha me, VA co con chau (goc cua cay)
    Khong the coi moi nguoi khong cha me la 'doi 1' -
    cac ba dau cung khong co cha me trong cay nhung ho khong phai thuy to.
    """
    con_cua = {}   # con -> gia dinh cha me
    for fid, f in fams.items():
        for c in f['con']:
            con_cua[c] = fid

    # Buoc 1: xac dinh ai la huyet thong.
    # Huyet thong = co cha/me trong cay, HOAC la goc (khong cha me + co con).
    co_con = set()
    for f in fams.values():
        if f['con']:
            for x in (f['chong'], f['vo']):
                if x:
                    co_con.add(x)

    huyet_thong = set()
    for pid in people:
        if pid in con_cua:
            huyet_thong.add(pid)   # co cha me -> chac chan huyet thong

    # Goc: khong cha me, co con, va KHONG phai vo/chong cua nguoi huyet thong khac.
    # Vo/chong cua nguoi huyet thong ma khong co cha me -> la dau/re.
    la_vo_chong_cua = defaultdict(set)
    for f in fams.values():
        if f['chong'] and f['vo']:
            la_vo_chong_cua[f['chong']].add(f['vo'])
            la_vo_chong_cua[f['vo']].add(f['chong'])

    for pid in people:
        if pid in huyet_thong:
            continue
        if pid not in co_con:
            continue
        # co con nhung khong cha me. La goc hay la dau/re?
        bans = la_vo_chong_cua.get(pid, set())
        if any(b in huyet_thong for b in bans):
            continue          # ban doi la huyet thong -> minh la dau/re
        huyet_thong.add(pid)  # khong ai neo vao -> la goc that

    memo = {}

    def doi_huyet(pid, depth=0):
        """Doi cua nguoi huyet thong: dem tu goc xuong."""
        if pid in memo:
            return memo[pid]
        if depth > 60:
            return 1
        memo[pid] = 1
        fid = con_cua.get(pid)
        if not fid:
            memo[pid] = 1
            return 1
        f = fams[fid]
        # chi tinh theo cha me HUYET THONG (bo qua dau/re)
        cha_me = [x for x in (f['chong'], f['vo']) if x and x in huyet_thong]
        if not cha_me:
            cha_me = [x for x in (f['chong'], f['vo']) if x]
        if not cha_me:
            memo[pid] = 1
            return 1
        d = max(doi_huyet(x, depth + 1) for x in cha_me) + 1
        memo[pid] = d
        return d

    for pid in people:
        if pid in huyet_thong:
            people[pid]['doi'] = doi_huyet(pid)
            people[pid]['huyet_thong'] = True
        else:
            people[pid]['huyet_thong'] = False

    # Buoc 2: dau/re lay doi theo vo/chong
    for pid, p in people.items():
        if p.get('huyet_thong'):
            continue
        doi_ban = [people[b]['doi'] for b in la_vo_chong_cua.get(pid, set())
                   if b in people and 'doi' in people[b]]
        p['doi'] = min(doi_ban) if doi_ban else 0

    return people


def duong_dan(people, fams):
    """Duong tu thuy to xuong tung nguoi: [thuy to, ..., nguoi do]."""
    con_cua = {}
    for fid, f in fams.items():
        for c in f['con']:
            con_cua[c] = fid

    def path(pid, seen=None):
        if seen is None:
            seen = set()
        if pid in seen:
            return []
        seen.add(pid)
        fid = con_cua.get(pid)
        if not fid:
            return [pid]
        f = fams[fid]
        # uu tien duong theo cha (huyet thong dong ho Pham Dinh)
        cha = f['chong'] or f['vo']
        if not cha:
            return [pid]
        return path(cha, seen) + [pid]

    for pid in people:
        people[pid]['duong'] = path(pid)
    return people


def xuat_gedcom_loc(src, dest, people):
    """
    Xuat GEDCOM DA LOC de dung voi Topola.

    Nguyen tac giong het data.json: CAT LUC XUAT, khong cat luc hien thi.
    File nay se nam cong khai tren GitHub, nen moi thu trong no la cong khai.

    Thay doi so voi ban goc:
      - Nguoi CON SONG: '1 BIRT / 2 DATE 10 APR 1933' -> '2 DATE 1933'
      - Xoa cac dong 'DATE ...' vo nghia (MyHeritage sinh ra)
      - Xoa RESI/ADDR (chua email, dia chi - khong nen cong khai)
      - Xoa OBJE (link anh MyHeritage da het han, vo dung)
      - Xoa _UID/_UPD/RIN (dinh danh noi bo MyHeritage)
    """
    txt = open(src, encoding='utf-8-sig').read().replace('\r\n', '\n')
    recs = re.split(r'\n(?=0 )', txt)

    con_song = {pid for pid, p in people.items() if p['con_song']}
    out = []

    BO_TAG = ('_UID', '_UPD', 'RIN', '_PROJECT_GUID', '_EXPORTED_FROM_SITE_ID')

    for rec in recs:
        lines = rec.split('\n')
        head = lines[0]

        mi = re.match(r'^0 @(I[^@]+)@ INDI$', head)
        pid = mi.group(1) if mi else None
        song = pid in con_song if pid else False

        giu = []
        i = 0
        while i < len(lines):
            ln = lines[i]
            if not ln.strip():
                i += 1
                continue

            m = re.match(r'^(\d+) (\S+)(.*)$', ln)
            if not m:
                i += 1
                continue
            lvl, tag = int(m.group(1)), m.group(2)

            # Bo hang loat khoi con: RESI (email/dia chi), OBJE (anh het han)
            if lvl == 1 and tag in ('RESI', 'OBJE'):
                i += 1
                while i < len(lines) and re.match(r'^([2-9]|\d\d) ', lines[i]):
                    i += 1
                continue

            # Bo dinh danh noi bo
            if tag in BO_TAG:
                i += 1
                continue

            # BIRT cua nguoi CON SONG: cat ngay/thang, chi giu nam
            if lvl == 1 and tag == 'BIRT':
                giu.append(ln)
                i += 1
                while i < len(lines) and re.match(r'^([2-9]|\d\d) ', lines[i]):
                    sub = lines[i]
                    md = re.match(r'^(\d+) DATE (.+)$', sub)
                    if md:
                        d = md.group(2).strip()
                        if d == '...' or not d:
                            i += 1
                            continue          # bo dong vo nghia
                        if song:
                            nam = re.search(r'\b(\d{4})\b', d)
                            if nam:
                                giu.append(f'{md.group(1)} DATE {nam.group(1)}')
                            i += 1
                            continue
                    giu.append(sub)
                    i += 1
                continue

            # DEAT: bo hoan toan neu nguoi con song (co 'DEAT Y' gia)
            if lvl == 1 and tag == 'DEAT':
                if song:
                    i += 1
                    while i < len(lines) and re.match(r'^([2-9]|\d\d) ', lines[i]):
                        i += 1
                    continue
                giu.append(ln)
                i += 1
                while i < len(lines) and re.match(r'^([2-9]|\d\d) ', lines[i]):
                    sub = lines[i]
                    md = re.match(r'^(\d+) DATE (.+)$', sub)
                    if md and md.group(2).strip() in ('...', ''):
                        i += 1
                        continue
                    giu.append(sub)
                    i += 1
                continue

            giu.append(ln)
            i += 1

        if giu:
            out.append('\n'.join(giu))

    with open(dest, 'w', encoding='utf-8') as fo:
        fo.write('\n'.join(out).rstrip() + '\n')

    return dest


def ngay_viet(s):
    """'16 APR 1995' -> '16/4/1995'. Chi ap dung cho nguoi da mat."""
    if not s:
        return s
    THANG = {'JAN': 1, 'FEB': 2, 'MAR': 3, 'APR': 4, 'MAY': 5, 'JUN': 6,
             'JUL': 7, 'AUG': 8, 'SEP': 9, 'OCT': 10, 'NOV': 11, 'DEC': 12}
    m = re.fullmatch(r'(\d{1,2})\s+([A-Z]{3})\s+(\d{4})', s.strip().upper())
    if m:
        return f'{int(m.group(1))}/{THANG[m.group(2)]}/{m.group(3)}'
    m = re.fullmatch(r'([A-Z]{3})\s+(\d{4})', s.strip().upper())
    if m:
        return f'tháng {THANG[m.group(1)]}/{m.group(2)}'
    return s.strip()


def main():
    people, fams = parse()
    people = tinh_doi(people, fams)
    people = duong_dan(people, fams)

    # bo sung: quan he nguoc, khoa tim kiem
    for pid, p in people.items():
        p['tim'] = bo_dau(p['ten'])
        p['con_song'] = (p['mat'] == '')

        # ===== LOC RIENG TU: nguoi CON SONG chi hien NAM sinh =====
        # Cat ngay/thang NGAY TU LUC XUAT - khong ghi vao data.json.
        # Day la cach phan quyen duy nhat co that tren trang tinh:
        # loc luc xuat, khong loc luc hien thi. Du lieu da cat thi
        # khong ai lay lai duoc, ke ca khi mo thang file JSON.
        if p['con_song'] and p['sinh']:
            nam = re.search(r'\b(\d{4})\b', p['sinh'])
            p['sinh'] = nam.group(1) if nam else ''
        # nguoi da mat: giu nguyen ngay thang day du (de gio chap, cung gio)
        else:
            p['sinh'] = ngay_viet(p['sinh'])
        p['mat'] = ngay_viet(p['mat'])

        # vo/chong + con
        vo_chong, con = [], []
        for fid in p['fams']:
            f = fams.get(fid)
            if not f:
                continue
            other = f['vo'] if f['chong'] == pid else f['chong']
            if other:
                vo_chong.append(other)
            con.extend(f['con'])
        p['vo_chong'] = vo_chong
        p['con'] = con
        # cha me
        cha, me = None, None
        if p['famc'] and p['famc'] in fams:
            cha = fams[p['famc']]['chong']
            me = fams[p['famc']]['vo']
        p['cha'] = cha
        p['me'] = me
        # anh em
        anh_em = []
        if p['famc'] and p['famc'] in fams:
            anh_em = [c for c in fams[p['famc']]['con'] if c != pid]
        p['anh_em'] = anh_em

        # ===== Bo cac truong khong nen cong khai =====
        # 'anh': link anh MyHeritage - da het han chu ky nen vo dung,
        #        lai lo dinh danh trang MyHeritage cua chu ho.
        # 'famc': dinh danh gia dinh noi bo - da dung xong o tren, trang khong can.
        p.pop('anh', None)
        p.pop('famc', None)
        p.pop('fams', None)

    # 'giadinh' khong duoc trang dung den -> khong ghi ra, cho nhe file
    data = {
        'nguoi': people,
        'tong': len(people),
        'ten_cay': 'Gia phả PHẠM ĐÌNH — xã Hà Bắc',
    }

    import os
    os.makedirs(os.path.dirname(OUT) or '.', exist_ok=True)
    with open(OUT, 'w', encoding='utf-8') as fo:
        json.dump(data, fo, ensure_ascii=False, separators=(',', ':'))

    # Xuat GEDCOM DA LOC cho Topola (cung thu muc voi data.json)
    ged_out = os.path.join(os.path.dirname(OUT) or '.', 'giapha.ged')
    xuat_gedcom_loc(SRC, ged_out, people)

    # thong ke
    song = sum(1 for p in people.values() if p['con_song'])
    print(f'Tong: {len(people)} nguoi, {len(fams)} gia dinh')
    print(f'Con song (khong co ngay mat): {song}')
    print(f'Da mat (co ngay mat that): {len(people) - song}')
    max_doi = max(p['doi'] for p in people.values())
    print(f'So doi: {max_doi}')
    for d in range(1, max_doi + 1):
        n = sum(1 for p in people.values() if p['doi'] == d)
        print(f'  Doi {d}: {n} nguoi')
    thuyto = [p['ten'] for p in people.values() if p['doi'] == 1 and p['huyet_thong']]
    print(f'Thuy to: {thuyto[0] if thuyto else "?"}')
    print()
    print(f'Ghi ra: {OUT}')
    print(f'Ghi ra: {ged_out}  (GEDCOM da loc, cho Topola)')


if __name__ == '__main__':
    main()
