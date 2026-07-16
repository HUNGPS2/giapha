#!/usr/bin/env python3
"""
Chuyen GEDCOM (xuat tu MyHeritage) sang JSON cho trang gia pha.
Xu ly rieng cho du lieu tieng Viet:
  - Bo co DEAT Y gia (MyHeritage gan cho ca nguoi song)
  - Chuan hoa ten (4 kieu viet khac nhau)
  - Sinh khoa tim kiem khong dau
  - Tinh doi (generation) tu thuy to
"""
import html
import re, json, unicodedata, sys
from collections import defaultdict

SRC = sys.argv[1] if len(sys.argv) > 1 else 'giapha-goc.ged'
OUT = sys.argv[2] if len(sys.argv) > 2 else 'data.json'

# ─────────────────────────────────────────────────────────────
#  HAI MOC DE SUY TRANG THAI  — sua o day neu can
# ─────────────────────────────────────────────────────────────

# Doi <= moc nay: coi la DA MAT, du khong co ngay mat.
# Cac cu to tien xa khong ai ghi lai ngay mat, nhung chac chan da khuat.
# Doi 11 la doi cuoi cung khong con ai song (theo xac nhan cua chu ho).
DOI_CHAC_MAT = 11

# Sinh truoc nam nay ma khong co ngay mat -> CHUA RO (khong dam noi song hay mat).
# 1920 => nay 106 tuoi. Chon moc cao cho an toan: tha ghi 'chua ro'
# con hon khang dinh nham mot cu con song da khuat tu lau.
NAM_NGUONG = 1920


def bo_dau(s):
    """Bo dau tieng Viet -> chuoi khong dau, chu thuong. Dung cho tim kiem."""
    s = s.replace('Đ', 'D').replace('đ', 'd')
    s = unicodedata.normalize('NFD', s)
    s = ''.join(c for c in s if unicodedata.category(c) != 'Mn')
    return s.lower()


def chuan_hoa_ten(raw):
    """
    GEDCOM ghi ten dang:  TEN /HO/

    Hai cach chu ho da dung:

      CACH CU (MyHeritage khong hien ho truoc ten, nen go het vao truong ten):
        'PHẠM ĐÌNH QUỲNH //'      -> ho TRONG
        '1. PHẠM ĐÌNH MIỆN //'    -> co so thu tu anh em
        'XI.7.PHẠM ĐÌNH THẠC //'  -> co so doi + so thu tu

      CACH MOI (go ho rieng, ten+dem rieng):
        'Đình Quỳnh /Phạm/'       -> ghep thanh 'Phạm Đình Quỳnh'
        '1. Đình Miện /Phạm/'     -> ghep + giu so
        'Quốc Khánh /Lê/'         -> ho khac -> 'Lê Quốc Khánh'

    Tra ve: (ten_hien_thi, so_thu_tu)

    QUAN TRONG - THU TU XU LY:
      Phai TACH SO TRUOC, roi moi GHEP HO.
      Neu ghep ho truoc: '1. Đình Miện /Phạm/' -> 'Phạm 1. Đình Miện'
      -> so bi ket giua ten, khong nhan ra duoc nua.
    """
    raw = raw.strip()

    # ── 1. Tach ho / ten ────────────────────────────────────
    m = re.match(r'^(.*?)/(.*?)/(.*)$', raw)
    if m:
        truoc, ho, sau = m.group(1).strip(), m.group(2).strip(), m.group(3).strip()
    else:
        truoc, ho, sau = raw, '', ''

    # ── 2. TACH SO khoi phan TEN (truoc khi ghep ho) ────────
    so = None
    tien_to = ''          # 'XI.7.' - giu lai trong ten hien thi

    # Kieu 'XI.7.' hoac 'XI.7. ' - so doi (La Ma) + so thu tu
    m_lama = re.match(r'^([IVX]+)\.(\d+)\.\s*(.*)$', truoc)
    if m_lama:
        so = int(m_lama.group(2))
        tien_to = f'{m_lama.group(1)}.{m_lama.group(2)}.'
        truoc = m_lama.group(3)
    else:
        # Kieu 'XI.' - chi co so doi, khong co so thu tu
        m_doi = re.match(r'^([IVX]+)\.\s*(\D.*)$', truoc)
        if m_doi:
            tien_to = f'{m_doi.group(1)}.'
            truoc = m_doi.group(2)
        else:
            # Kieu '1.' / '9.' / '12 -' - so thu tu anh em
            m_so = re.match(r'^\s*(\d+)\s*[.\-)]\s*(.+)$', truoc)
            if m_so:
                so = int(m_so.group(1))
                truoc = m_so.group(2)      # BO so khoi ten hien thi, GIU gia tri

    # ── 3. Ghep ho + ten theo dung thu tu nguoi Viet ────────
    if ho:
        ten = f'{ho} {truoc} {sau}'.strip()      # 'Phạm' + 'Đình Quỳnh'
    else:
        ten = f'{truoc} {sau}'.strip()           # ho trong -> ten da day du

    # Tien to 'XI.7.' dat len dau - dong ho dung no de goi cac cu
    if tien_to:
        ten = f'{tien_to}{ten}'

    ten = re.sub(r'\s+', ' ', ten).strip()
    return ten, so


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


def la_rac_gramps(nd):
    """
    Gramps tu sinh GHI CHU RAC khi nhap file MyHeritage.

    Gap cac the rieng cua MyHeritage ma no khong hieu (_FILESIZE, _CUTOUT,
    _PHOTO_RIN...), no ghi lai thanh mot 'note' roi GAN VAO NGUOI:

        Records not imported into INDI (individual) Gramps ID I500081:
        Line ignored as not understood       Line 837: 2 _FILESIZE 73223
        Line ignored as not understood       Line 839: 2 _CUTOUT Y
        ...

    Day la NHAT KY LOI cua Gramps, khong phai ghi chu ve nguoi do.
    Trong file cua chu ho: 24/27 note la loai nay, 22 nguoi bi dinh.
    Phai bo, neu khong nguoi doc se thay bao loi thay vi chuyen doi cu.
    """
    if not nd:
        return False
    dau = nd[:200]
    return bool(
        re.search(r'not imported into|Line ignored as not understood|'
                  r'Records not imported', dau, re.I)
    )


def doc_note_rieng(recs):
    """
    Gramps tach NOTE ra BAN GHI RIENG, nguoi chi tro toi:
        1 NOTE @N0027@
        ...
        0 @N0027@ NOTE Luc sinh thoi Cu giu chuc...
        1 CONC  i la Cu Huyen Quynh...
        1 CONT
        1 CONT Cu da chu tri hoi hop...

    MyHeritage thi nhung thang vao nguoi:
        1 NOTE Luc sinh thoi...

    Ham nay doc het cac ban ghi NOTE rieng, tra ve {ma: noi_dung}.

    CONC = noi TIEP dong truoc, KHONG them khoang trang
           ('go' + 'i la' -> 'goi la')
    CONT = XUONG DONG moi
    """
    ket_qua = {}
    for r in recs:
        m = re.match(r'^@(N[^@]+)@ NOTE\s?(.*)$', r['head'])
        if not m:
            continue
        ma = m.group(1)
        phan = [m.group(2)]              # phan noi dung ngay tren dong '0 @N@ NOTE ...'
        for lvl, val in r['raw']:
            if val.startswith('CONC '):
                phan.append(val[5:])     # noi TIEP - khong them gi
            elif val == 'CONC':
                pass
            elif val.startswith('CONT '):
                phan.append('\n' + val[5:])
            elif val == 'CONT':
                phan.append('\n')
        nd = ''.join(phan).strip()
        if la_rac_gramps(nd):
            continue                 # nhat ky loi cua Gramps - khong phai ghi chu
        ket_qua[ma] = nd
    return ket_qua


def parse():
    recs = doc_gedcom(SRC)
    people, fams = {}, {}

    # Doc truoc cac ban ghi NOTE rieng (kieu Gramps)
    note_rieng = doc_note_rieng(recs)

    for r in recs:
        head = r['head']
        mi = re.match(r'^@(I[^@]+)@ INDI$', head)
        mf = re.match(r'^@(F[^@]+)@ FAM$', head)

        if mi:
            pid = mi.group(1)
            p = {'id': pid, 'ten': '', 'so_ten': None,
                 'gioi': '', 'sinh': '', 'mat': '',
                 'noi_sinh': '', 'noi_mat': '', 'mo': '', 'lap_nghiep': '', 'ghi_chu': '',
                 'fams': [], 'famc': None, 'anh': []}
            i = 0
            raw = r['raw']
            while i < len(raw):
                lvl, val = raw[i]
                if lvl == 1:
                    tag = val.split(' ', 1)[0]
                    arg = val[len(tag):].strip()

                    if tag == 'NAME':
                        p['ten'], p['so_ten'] = chuan_hoa_ten(arg)
                    elif tag == 'SEX':
                        p['gioi'] = arg
                    elif tag == 'FAMS':
                        p['fams'].append(arg.strip('@'))
                    elif tag == 'FAMC':
                        p['famc'] = arg.strip('@')

                    elif tag == 'NOTE':
                        # Hai kieu:
                        #   Gramps      : '1 NOTE @N0027@'  -> con tro, tra bang
                        #   MyHeritage  : '1 NOTE Luc sinh thoi...' -> noi dung thang
                        m_tro = re.fullmatch(r'@(N[^@]+)@', arg.strip())
                        if m_tro:
                            gc = note_rieng.get(m_tro.group(1), '')
                            j = i + 1
                            while j < len(raw) and raw[j][0] > 1:
                                j += 1
                        else:
                            noi_dung = [arg] if arg else []
                            j = i + 1
                            while j < len(raw) and raw[j][0] > 1:
                                sub = raw[j][1]
                                if sub.startswith('CONT '):
                                    noi_dung.append('\n' + sub[5:])
                                elif sub == 'CONT':
                                    noi_dung.append('\n')
                                elif sub.startswith('CONC '):
                                    noi_dung.append(sub[5:])   # noi tiep, KHONG them dau cach
                                j += 1
                            gc = ''.join(noi_dung).strip()
                            if la_rac_gramps(gc):
                                gc = ''

                        if gc:
                            p['ghi_chu'] = (p['ghi_chu'] + '\n\n' + gc).strip() \
                                           if p['ghi_chu'] else gc
                        i = j - 1

                    elif tag in ('BIRT', 'DEAT', 'BURI', 'RESI'):
                        # doc cac dong con (level 2)
                        j = i + 1
                        date, plac = '', ''
                        while j < len(raw) and raw[j][0] > 1:
                            sub = raw[j][1]
                            if sub.startswith('DATE '):
                                date = sub[5:].strip()
                            elif sub.startswith('PLAC '):
                                plac = sub[5:].strip()
                            elif sub.startswith('NOTE '):
                                # Note GAN VOI SU KIEN (khong phai note cua nguoi).
                                nt = sub[5:].strip()
                                m_tro = re.fullmatch(r'@(N[^@]+)@', nt)
                                gc2 = note_rieng.get(m_tro.group(1), '') if m_tro else nt
                                if gc2:
                                    # Note cua su kien MAT ma noi ve AN TANG
                                    # -> day la MO PHAN, khong phai ghi chu.
                                    # (Chu ho ghi noi an tang vao o Description
                                    #  cua su kien Death, thay vi truong Burial.)
                                    if tag == 'DEAT' and re.search(
                                            r'an táng|chôn|mai táng|nghĩa trang|mộ',
                                            gc2, re.I):
                                        if not p['mo']:
                                            p['mo'] = gc2
                                    else:
                                        p['ghi_chu'] = (p['ghi_chu'] + '\n\n' + gc2).strip() \
                                                       if p['ghi_chu'] else gc2
                            j += 1
                        # QUAN TRONG: du lieu rac cho nguoi CON SONG:
                        #   MyHeritage: '1 DEAT Y' + '2 DATE ...'
                        #   Gramps    : '1 DEAT'   + '2 DATE ...'  (khong co chu Y)
                        # Ca hai deu phai coi la RONG.
                        if date == '...' or date == '':
                            date = ''
                        if tag == 'BIRT':
                            p['sinh'] = date
                            p['noi_sinh'] = plac
                        elif tag == 'DEAT':
                            p['mat'] = date          # rong = con song / khong ro
                            p['noi_mat'] = plac
                        elif tag == 'RESI':
                            # RESI = Residence, dung lam 'Noi lap nghiep'.
                            # NHUNG o nay chu ho co the go nham email hoac dia chi
                            # nha rieng -> LOC BO, khong dua len trang cong khai.
                            noi = (plac or '').strip()
                            la_email = '@' in noi
                            la_dia_chi = bool(re.search(
                                r'số nhà|ngõ|ngách|hẻm|đường|phố|thôn|xóm|/'
                                r'|\bp\.|\bq\.|\bkp\b', noi, re.I))
                            if noi and not la_email and not la_dia_chi:
                                p['lap_nghiep'] = noi
                        else:                        # BURI - noi an tang
                            # Con chau can NOI DAT MO de tao mo, hon la ngay an tang.
                            p['mo'] = plac or date
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

        # Di theo NGUOI MANG DONG MAU HO PHAM, du la cha hay me.
        #
        # Truoc day luon di theo CHA. Sai voi CHAU NGOAI:
        # Le Quoc Khanh co cha la re Le Cu (nguoi ngoai ho), me la
        # Pham Thi Dung (con gai ho Pham). Di theo cha -> duong dan chi
        # 'Le Cu -> Le Quoc Khanh', mat het lien he voi ho Pham.
        #
        # Di theo me -> 'Thuy to -> ... -> Pham Thi Dung -> Le Quoc Khanh'.
        # Dung: chau ngoai VAN thuoc dong ho, qua duong me.
        cha_me = [x for x in (f['chong'], f['vo']) if x]
        huyet = [x for x in cha_me
                 if x in people and people[x].get('huyet_thong')]

        if huyet:
            tiep = huyet[0]          # uu tien nguoi mang dong mau ho Pham
        elif cha_me:
            tiep = cha_me[0]         # ca hai deu ngoai ho -> theo cha
        else:
            return [pid]

        return path(tiep, seen) + [pid]

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

        # BO HAN cac ban ghi OBJE (anh) va NOTE o cap 0.
        # Gramps tach chung ra ban ghi rieng: '0 @O0000@ OBJE'.
        #   - OBJE: chua link anh MyHeritage DA CHET (chu ky het han) -> vo dung,
        #           lai lo dinh danh trang MyHeritage cua chu ho.
        #   - NOTE: van ban tu do, co the lan so dien thoai/dia chi.
        # Topola chi ve so do cay, khong can hai thu nay.
        if re.match(r'^0 @[NO][^@]*@ (NOTE|OBJE)\b', head):
            continue

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

            # BO HOAN TOAN 'NOTE' khoi GEDCOM xuat ra.
            # NOTE la van ban tu do, co the lan so dien thoai/dia chi.
            # Trang chinh (data.json) hien NOTE nhung DA LOC bang loc_ghi_chu().
            # File GEDCOM nay chi de ve so do cay - Topola khong can NOTE,
            # nen bo han cho chac, khong phai loc lai lan hai.
            # Bo NOTE o MOI CAP (1 va 2). Ban ghi dich da bi xoa o tren,
            # de lai con tro treo lo lung ('2 NOTE @N0025@') thi khong sach.
            if tag == 'NOTE':
                i += 1
                while i < len(lines) and re.match(r'^(\d+) ', lines[i]) \
                      and int(re.match(r'^(\d+) ', lines[i]).group(1)) > lvl:
                    i += 1
                continue

            # BIRT cua nguoi CON SONG: cat ngay/thang, chi giu nam
            if lvl == 1 and tag == 'BIRT':
                giu.append(ln)
                i += 1
                while i < len(lines) and re.match(r'^([2-9]|\d\d) ', lines[i]):
                    sub = lines[i]
                    # Bo con tro NOTE (ban ghi dich da xoa -> treo lo lung)
                    if re.match(r'^\d+ NOTE\b', sub):
                        i += 1
                        continue
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
                    if re.match(r'^\d+ NOTE\b', sub):     # con tro NOTE treo lo lung
                        i += 1
                        continue
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


def tach_chu_thich_anh(gc):
    """
    Tach CHU THICH ANH TU LIEU ra khoi phan ke chuyen trong Note.

    Chu ho go trong Note cua Gramps:

        Luc sinh thoi Cu giu chuc Tri huyen...

        Cu da chu tri hoi hop hai xa...

        [tl1] Bia Pha ky ho Pham, lap nam 1891
        [tl2] Mo cu tai Dong Dong, Cau La

    Tra ve: (phan_ke_chuyen, {1: 'Bia Pha ky...', 2: 'Mo cu tai...'})

    Anh tu lieu dat ten:  <ten-nguoi>-tl1.jpg, -tl2.jpg
    Chan dung dat ten :   <ten-nguoi>.jpg, -2.jpg, -3.jpg
    -> Hai loai TACH BACH, khong lan lon.
    """
    if not gc:
        return '', {}

    chu_thich = {}
    con_lai = []
    for dong in gc.split('\n'):
        # Bat '[tl1] ...' - ke ca khi khong o dau dong.
        # Chu ho co the go '[tl1]An tang tai...' lien nhau, hoac go vao
        # o Description cua su kien (khong xuong dong).
        m = re.match(r'^\s*\[tl(\d+)\]\s*(.*)$', dong, re.I)
        if m:
            chu_thich[int(m.group(1))] = m.group(2).strip()
            continue

        # '[tl1]' nam GIUA dong -> tach phan sau lam chu thich,
        # phan truoc giu lai.
        m2 = re.search(r'\[tl(\d+)\]\s*(.*)$', dong, re.I)
        if m2:
            truoc = dong[:m2.start()].strip()
            chu_thich[int(m2.group(1))] = m2.group(2).strip()
            if truoc:
                con_lai.append(truoc)
            continue

        con_lai.append(dong)

    ke = re.sub(r'\n{3,}', '\n\n', '\n'.join(con_lai)).strip()
    return ke, chu_thich


def loc_ghi_chu(gc, con_song):
    """
    NOTE la van ban TU DO - co the lan so dien thoai, email, dia chi nha,
    chuyen rieng tu. File nay se nam CONG KHAI tren GitHub.

    Xoa moi thu co the dinh danh mot nguoi dang song:
      - so dien thoai VN (09xx, 03xx, +84...)
      - email
      - so nha / dia chi chi tiet
      - CMND / CCCD

    Xoa voi CA HAI: nguoi song va nguoi mat. So dien thoai cua cu da mat
    thuong la so cua con chau dang song - cung khong nen cong khai.
    """
    if not gc:
        return ''

    # ── GO HTML ──────────────────────────────────────────────
    # MyHeritage luu note bang trinh soan thao rich-text, nen xuat ra
    # co the lan '<p>', '&ugrave;', '&agrave;'... Phai go sach,
    # neu khong nguoi doc se thay ma HTML tho tren trang.
    gc = re.sub(r'<br\s*/?>', '\n', gc, flags=re.I)
    gc = re.sub(r'</p\s*>', '\n\n', gc, flags=re.I)
    gc = re.sub(r'<[^>]+>', '', gc)          # bo moi the con lai
    gc = html.unescape(gc)                   # '&ugrave;' -> 'ù'
    gc = re.sub(r'\n{3,}', '\n\n', gc)       # gop nhieu dong trong

    # So dien thoai VN: 09xxxxxxxx, 0912-345-678, +84 91 234 5678
    gc = re.sub(r'(?:\+?84|0)[\s.\-]?\d{2,3}[\s.\-]?\d{3,4}[\s.\-]?\d{3,4}',
                '[đã ẩn]', gc)
    # Email
    gc = re.sub(r'[\w.+-]+@[\w-]+\.[\w.]+', '[đã ẩn]', gc)
    # CMND 9 so / CCCD 12 so
    gc = re.sub(r'\b\d{9}\b|\b\d{12}\b', '[đã ẩn]', gc)

    # Dia chi nha: bat CA CUM, khong chi so nha.
    # 'so nha 12 ngo 34 pho Bach Mai' -> phai xoa het, khong chi '12'.
    # Bat tu khoa dia chi + moi thu den het cau.
    gc = re.sub(
        r'(?:số nhà|nhà số|địa chỉ|ngụ tại|sống tại|trú tại|ở tại)\s*[:\s].*?(?=[.;\n]|$)',
        '[đã ẩn]', gc, flags=re.I)
    # Cum 'so N ngo/ngach/hem/duong/pho ...'
    gc = re.sub(
        r'\b(?:số\s*)?\d+[A-Za-z]?(?:\s*/\s*\d+)?\s*'
        r'(?:ngõ|ngách|hẻm|đường|phố|thôn|xóm|tổ|khu|ấp)\s+[^.;\n]*',
        '[đã ẩn]', gc, flags=re.I)

    # Don dep: nhieu '[da an]' lien tiep -> gop lam mot
    gc = re.sub(r'(\[đã ẩn\][\s,]*){2,}', '[đã ẩn] ', gc)

    return gc.strip()


def ngay_viet(s):
    """
    Chuan hoa ngay thang ve dang Viet.

    Gia pha Viet co mot dang rat pho bien ma chuan GEDCOM khong lo:
    CU TO CHI CON NGAY GIO, KHONG CON NAM MAT.
    Vi du: VIII.PHAM QUANG THUC -> '23/02', IX.PHAM DINH BINH -> '14/01'.
    Nam mat that lac qua nhieu doi, nhung ngay gio thi con - vi moi nam
    con chau van cung. Ngay gio moi la thu quan trong, khong phai nam.

    Cac dang xu ly:
      '16 APR 1995' -> '16/4/1995'
      'APR 1995'    -> 'thang 4/1995'
      '23/02'       -> '23/2'        (ngay gio, khong nam - GIU LAI)
      '1995'        -> '1995'
    """
    if not s:
        return s
    s = s.strip()

    THANG = {'JAN': 1, 'FEB': 2, 'MAR': 3, 'APR': 4, 'MAY': 5, 'JUN': 6,
             'JUL': 7, 'AUG': 8, 'SEP': 9, 'OCT': 10, 'NOV': 11, 'DEC': 12}

    # '16 APR 1995' -> '16/4/1995'
    m = re.fullmatch(r'(\d{1,2})\s+([A-Z]{3})\s+(\d{4})', s.upper())
    if m:
        return f'{int(m.group(1))}/{THANG[m.group(2)]}/{m.group(3)}'

    # 'APR 1995' -> 'thang 4/1995'
    m = re.fullmatch(r'([A-Z]{3})\s+(\d{4})', s.upper())
    if m:
        return f'tháng {THANG[m.group(1)]}/{m.group(2)}'

    # '23/02' hoac '23/2' -> '23/2'  (NGAY GIO, KHONG CO NAM)
    # Bo so 0 dau cho gon, nhung GIU NGUYEN thong tin.
    m = re.fullmatch(r'(\d{1,2})\s*/\s*(\d{1,2})', s)
    if m:
        ngay, thang = int(m.group(1)), int(m.group(2))
        if 1 <= ngay <= 31 and 1 <= thang <= 12:
            return f'{ngay}/{thang}'

    # '23 APR' -> '23/4'  (ngay gio kieu GEDCOM chuan: ngay truoc, thang sau)
    m = re.fullmatch(r'(\d{1,2})\s+([A-Z]{3})', s.upper())
    if m and m.group(2) in THANG:
        return f'{int(m.group(1))}/{THANG[m.group(2)]}'

    # 'APR 19' -> '19/4'  (thang truoc, ngay sau - kieu My)
    # Nguoi dung go ngay gio khong nam theo thu tu thang/ngay.
    # Gramps giu nguyen vi khong phai ngay GEDCOM hop le, chi la van ban.
    m = re.fullmatch(r'([A-Z]{3})\s+(\d{1,2})', s.upper())
    if m and m.group(1) in THANG:
        return f'{int(m.group(2))}/{THANG[m.group(1)]}'

    return s


def main():
    people, fams = parse()
    people = tinh_doi(people, fams)
    people = duong_dan(people, fams)

    # Ghi lai cac truong hop SO TRONG TEN lech voi thu tu tren MyHeritage.
    lech_thu_tu = []

    # Chup lai 'so_ten' cua MOI NGUOI truoc vong lap.
    # Trong vong lap, p.pop('so_ten') xoa truong nay khoi tung nguoi -
    # nen khi xet anh em cua nguoi sau, so_ten cua nguoi truoc da mat.
    so_cua = {pid: p['so_ten'] for pid, p in people.items()}

    # bo sung: quan he nguoc, khoa tim kiem
    for pid, p in people.items():
        p['tim'] = bo_dau(p['ten'])

        # ===== BA TRANG THAI, khong phai hai =====
        # Truoc day: 'khong co ngay mat' => 'con song'. Sai voi cu thuy to
        # cach day 15 doi: cu khong co ngay mat, nhung chac chan da khuat.
        #
        #   da_mat   : co ngay/nam mat, HOAC o doi <= DOI_CHAC_MAT
        #   chua_ro  : sinh truoc NAM_NGUONG ma khong co ngay mat
        #   con_song : con lai
        #
        # KHONG suy 'khong co nam sinh' => 'chua ro'. Nhieu nguoi dang song
        # chi la chua nhap nam sinh; danh dau ho 'chua ro' la sai.
        # THIEU DU LIEU KHONG PHAI BANG CHUNG.

        nam_sinh = None
        if p['sinh']:
            m = re.search(r'\b(\d{4})\b', p['sinh'])
            if m:
                nam_sinh = int(m.group(1))

        if p['mat']:
            p['trang_thai'] = 'da_mat'
        elif nam_sinh and nam_sinh >= NAM_NGUONG:
            # NAM SINH THANG SUY LUAN THEO DOI.
            # Ai sinh sau 1920 thi khong the suy la 'da mat' chi vi o doi xa.
            # Neu khong co luat nay: them mot nguoi CON SONG vao doi 11
            # -> bi coi la da mat -> ngay/thang sinh KHONG bi cat -> LO.
            p['trang_thai'] = 'con_song'
        elif p['doi'] and p['doi'] <= DOI_CHAC_MAT:
            p['trang_thai'] = 'da_mat'      # to tien xa, khong co nam sinh gan day
        elif nam_sinh and nam_sinh < NAM_NGUONG:
            p['trang_thai'] = 'chua_ro'     # qua gia de con song, nhung khong dam khang dinh
        else:
            p['trang_thai'] = 'con_song'

        # 'con_song' van giu lai vi no DIEU KHIEN LOC RIENG TU.
        # Nguoi 'chua_ro' duoc bao ve NHU nguoi con song:
        # nghi ngo thi che, khong phoi bay.
        p['con_song'] = (p['trang_thai'] != 'da_mat')

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
        # Trong gia pha Viet, anh em CUNG CHA KHAC ME van la anh em ruot -
        # cung mot doi, cung mot chi. Cu Dinh 4 vo, con cua 4 ba deu la
        # anh em cua nhau.
        #
        # Con thuoc GIA DINH, nen con cua ba vo khac nam o gia dinh khac
        # cua cung nguoi cha. Phai gom con tu MOI gia dinh cha tham gia,
        # khong chi gia dinh sinh ra minh (famc).
        anh_em = []
        if cha:
            for f in fams.values():
                if f['chong'] == cha:            # moi gia dinh cua nguoi cha
                    for c in f['con']:
                        if c != pid and c not in anh_em:
                            anh_em.append(c)
        elif p['famc'] and p['famc'] in fams:
            # Khong ro cha (chi co me) -> lay anh em cung me
            anh_em = [c for c in fams[p['famc']]['con'] if c != pid]
        p['anh_em'] = anh_em

        # ===== THU TU GIA PHA =====
        # Sap theo VAN CHU CAI la sai voi gia pha. Gia pha xep theo
        # THU TU ANH EM trong nha: con truong truoc, con thu sau.
        #
        # NGUON THU TU - theo do tin cay giam dan:
        #
        #  1. SO TRONG TEN: 'XI.1.', 'XI.7.', 'XII.1.'
        #     Dong ho da tu danh so tu truoc. Day la nguon DANG TIN NHAT -
        #     do chinh nguoi trong ho ghi, dua tren gia pha goc.
        #
        #  2. Thu tu dong CHIL trong GEDCOM
        #     Chi la thu tu nhap lieu tren MyHeritage. Co the lech, vi
        #     chu ho nhap dan, khong nhat thiet theo thu tu sinh.
        #
        # Vi du that: cac cu doi 11 co so XI.1..XI.7 trong ten, nhung thu tu
        # CHIL lai la Thac(7) -> Ban(6) -> Dinh(1) - NGUOC HAN. Neu theo CHIL,
        # nhanh chi thu 7 se leo len dau, chi truong tut xuong duoi. Sai.
        p['thu_tu'] = 0
        p['nha'] = ''

        # ===== THU TU ANH EM TRONG NHA - BA TANG =====
        #
        #  Tang 1. SO TRONG TEN ('1. PHAM DINH MIEN', 'XI.7.PHAM DINH THAC')
        #          Do chu ho ghi tu gia pha goc -> DANG TIN NHAT. Luon thang.
        #
        #  Tang 2. NAM SINH (khi khong co so)
        #          Suy tu du lieu that, tot hon thu tu nhap lieu ngau nhien.
        #
        #  Tang 3. KHONG CO CA HAI -> xuong duoi cung, xep theo van chu cai.
        #
        # Vi sao SO phai thang NAM SINH:
        #   Nha cu Dinh: chi cu Do co nam sinh (1902), bon cu kia khong.
        #   Neu xep theo nam sinh, cu Do nhay len dau - DE MAT so chu ho
        #   da danh (Mien la con ca).
        #
        # Vi sao van can NAM SINH:
        #   Nha cu Do: cu co HAI VO, moi ba mot danh sach con, danh so RIENG
        #   -> thu tu CHIL bi trung (hai nguoi cung so 0, hai nguoi cung so 1).
        #   Nam sinh go duoc: 1928, 1929, 1930, 1933, 1934, 1935, 1942, 1945.

        nam_sinh_sap = None
        if p['sinh']:
            m_ns = re.search(r'\b(\d{4})\b', p['sinh'])
            if m_ns:
                nam_sinh_sap = int(m_ns.group(1))

        if p['so_ten'] is not None:
            # Tang 1: co so -> dung so. Nhan 10 de chua cho tang 2 chen vao giua.
            p['thu_tu'] = p['so_ten'] * 10
            p['co_so'] = True
        elif nam_sinh_sap:
            # Tang 2: khong so, co nam sinh -> xep theo nam.
            # +100000 de LUON nam duoi nguoi co so trong cung nha.
            p['thu_tu'] = 100000 + nam_sinh_sap
            p['co_so'] = False
        else:
            # Tang 3: khong ca hai -> xuong duoi cung.
            # Trong tang nay, ve() se xep tiep theo van chu cai.
            p['thu_tu'] = 900000
            p['co_so'] = False

        # Ghi lai neu hai nguon LECH nhau - de bao cuoi chuong trinh.
        # Phai lam O DAY, vi 'famc' bi xoa khoi dict o cuoi vong lap.
        if p['so_ten'] is not None and p['famc'] and p['famc'] in fams:
            ds_con = fams[p['famc']]['con']
            if pid in ds_con:
                theo_chil = ds_con.index(pid) + 1      # vi tri tren MyHeritage
                if p['so_ten'] != theo_chil:
                    lech_thu_tu.append((p['ten'], p['so_ten'], theo_chil))

        if p['famc'] and p['famc'] in fams:
            p['nha'] = p['famc']

        # ===== Bo cac truong khong nen cong khai =====
        # 'anh': link anh MyHeritage - da het han chu ky nen vo dung,
        #        lai lo dinh danh trang MyHeritage cua chu ho.
        # 'famc': dinh danh gia dinh noi bo - da dung xong o tren, trang khong can.
        p.pop('anh', None)
        p.pop('famc', None)
        p.pop('fams', None)
        p.pop('so_ten', None)

        # ===== TACH CHU THICH ANH TU LIEU '[tl1]' =====
        # Chu ho co the go '[tl1] ...' vao BAT KY o nao:
        #   - Note cua nguoi          (cho khuyen dung)
        #   - Note cua su kien
        #   - Description cua su kien Death  <- de nham vao day
        #
        # Quet CA BA cho. Neu chi quet Note, go nham cho se lam
        # '[tl1]' lot nguyen si ra trang (vd: Mo phan hien
        # '[tl1]An tang tai Dong Dong...').
        ct_gop = {}
        for truong in ('ghi_chu', 'mo', 'noi_sinh', 'noi_mat'):
            gt = p.get(truong, '')
            if gt and '[tl' in gt.lower():
                sach, ct = tach_chu_thich_anh(gt)
                p[truong] = sach
                ct_gop.update(ct)

        # NOTE la van ban tu do -> loc thong tin lien he truoc khi cong khai
        gc = loc_ghi_chu(p.get('ghi_chu', ''), p['con_song'])
        p['ghi_chu'], ct2 = tach_chu_thich_anh(gc)
        ct_gop.update(ct2)

        p['ct_anh'] = ct_gop

    # 'giadinh' khong duoc trang dung den -> khong ghi ra, cho nhe file
    # ===== KHOA SAP XEP THEO DONG DOI =====
    # De ca mot doi hien ra dung thu tu gia pha, can biet:
    # nha nay thuoc chi TRUONG hay chi THU, va o cap nao.
    #
    # Cach lam: di doc duong tu thuy to xuong, ghi lai 'con thu may'
    # o TUNG doi. Vd [0,0,2] = con truong cua con truong, la con thu 3.
    #
    # Bac DAU TIEN cua khoa: 0 = CHAU NOI (theo dong cha, mang ho Pham)
    #                        1 = CHAU NGOAI (cha la re, mang ho khac)
    # Chau ngoai luon xep SAU chau noi trong cung mot doi - dung loi gia pha.
    #
    # Vi du that: Le Quoc Khanh (cha la re Le Cu, me la Pham Thi Dung)
    # co duong dan chi 2 bac 'Le Cu -> Le Quoc Khanh', ngan hon con chau
    # ho Pham (14 bac). Neu khong tach chau ngoai ra, day ngan se xep TRUOC
    # day dai -> chau ngoai leo len dau doi. Sai.
    goc_ho = {pid for pid, p in people.items()
              if p['doi'] == 1 and p['huyet_thong']}

    for pid, p in people.items():
        # Chau noi: duong dan bat dau tu THUY TO cua ho Pham.
        # Chau ngoai: duong dan bat dau tu mot nguoi khac (ong ngoai/cha re).
        la_noi = bool(p['duong']) and p['duong'][0] in goc_ho
        khoa = [0 if la_noi else 1]
        for x in p['duong']:
            nx = people.get(x)
            khoa.append(nx['thu_tu'] if nx else 0)
        p['khoa_sap'] = khoa

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
    tt = {'da_mat': 0, 'chua_ro': 0, 'con_song': 0}
    for p in people.values():
        tt[p['trang_thai']] += 1
    co_ngay = sum(1 for p in people.values() if p['mat'])

    print(f'Tong: {len(people)} nguoi, {len(fams)} gia dinh')
    print(f'  Da mat  : {tt["da_mat"]:>3}  ({co_ngay} co ngay mat, '
          f'{tt["da_mat"] - co_ngay} suy tu doi <= {DOI_CHAC_MAT})')
    print(f'  Chua ro : {tt["chua_ro"]:>3}  (sinh truoc {NAM_NGUONG})')
    print(f'  Con song: {tt["con_song"]:>3}')
    max_doi = max(p['doi'] for p in people.values())
    print(f'So doi: {max_doi}')
    for d in range(1, max_doi + 1):
        n = sum(1 for p in people.values() if p['doi'] == d)
        print(f'  Doi {d}: {n} nguoi')
    thuyto = [p['ten'] for p in people.values() if p['doi'] == 1 and p['huyet_thong']]
    print(f'Thuy to: {thuyto[0] if thuyto else "?"}')

    # Canh bao nam sinh/mat vo ly (vd '892' - thieu chu so).
    # CHI canh bao, KHONG tu sua: doan mo y dinh cua chu ho la sai.
    # Bo qua dang '23/2' (ngay gio khong nam) - do la du lieu HOP LE.
    ngo = []
    for p in people.values():
        for truong in ('sinh', 'mat'):
            gt = p[truong] or ''
            if re.fullmatch(r'\d{1,2}/\d{1,2}', gt):
                continue                      # ngay gio, khong co nam - hop le
            m = re.search(r'\b(\d{3,4})\b', gt)
            if m:
                nam = int(m.group(1))
                if nam < 1500 or nam > 2030:
                    ngo.append((p['ten'], truong, gt))
    if ngo:
        print()
        print('CANH BAO — nam sinh/mat trong khong hop ly (sua trong MyHeritage):')
        for ten, truong, gt in ngo:
            print(f'  {ten[:30]:<32} {truong}="{gt}"')

    # Bao khi SO TRONG TEN lech voi thu tu tren MyHeritage.
    # Trang dung SO TRONG TEN (dang tin hon), nhung nen sua lai tren
    # MyHeritage cho khop, de sau nay them nguoi moi khong bi nham.
    if lech_thu_tu:
        print()
        print('LUU Y — so trong ten khac thu tu tren MyHeritage:')
        print('  (trang dung SO TRONG TEN. Nen sap lai tren MyHeritage cho khop.)')
        for ten, st, sc in lech_thu_tu:
            print(f'  {ten[:30]:<32} ten ghi {st}, MyHeritage xep {sc}')

    # Bao cac nha DANH SO DO DANG: mot so con co so, mot so chua.
    # Nguoi CHUA co so bi day xuong duoi - dung, nhung chu ho nen biet
    # de danh not cho tron.
    do_dang = []
    for fid, f in fams.items():
        con = [people[c] for c in f['con'] if c in people]
        if len(con) < 2:
            continue
        co = [c for c in con if c.get('co_so')]
        khong = [c for c in con if not c.get('co_so')]
        if co and khong:
            cha = people.get(f['chong'])
            do_dang.append((cha['ten'] if cha else '?', len(co), len(khong),
                            [c['ten'] for c in khong]))
    if do_dang:
        print()
        print('CHUA DANH SO XONG — cac nha co con vua co so vua chua:')
        print('  (nguoi chua co so bi xep XUONG DUOI. Danh not de dung thu tu.)')
        for cha, n_co, n_khong, ds_khong in do_dang:
            print(f'  Nha cụ {cha[:26]:<28} {n_co} da co so, {n_khong} chua:')
            for t in ds_khong:
                print(f'      {t[:34]}')
    print()
    print(f'Ghi ra: {OUT}')
    print(f'Ghi ra: {ged_out}  (GEDCOM da loc, cho Topola)')


if __name__ == '__main__':
    main()
