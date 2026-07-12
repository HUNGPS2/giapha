# Gia phả họ Phạm Đình — trang tĩnh

## Nội dung
- `index.html` — toàn bộ trang (tìm kiếm + trang cá nhân + đường dẫn nhánh)
- `data.json` — dữ liệu đã xử lý (159 người, 55 gia đình, 9 đời)
- `giapha.ged` — **GEDCOM đã lọc**, dùng cho nút "Xem sơ đồ cây" (Topola). File này do
  `convert.py` sinh ra, KHÔNG phải bản gốc từ MyHeritage. Xem mục Riêng tư bên dưới.
- `convert.py` — bộ chuyển GEDCOM → JSON (lọc dữ liệu riêng tư)
- `kiemtra.py` — kiểm tra an toàn trước khi push (dùng chung cho cả hai script)
- `ketnoi-github.bat` — **chạy MỘT LẦN** để nối thư mục với GitHub (Windows)
- `capnhat.bat` — **cập nhật, cho Windows** (kéo thả file .ged vào là chạy)
- `capnhat.sh` — cập nhật một lệnh, cho macOS/Linux

## Đưa lên GitHub Pages
1. Tạo repo mới trên GitHub (ví dụ `giapha`).
2. Đẩy 3 file: `index.html`, `data.json`, `giapha.ged`.
3. Vào **Settings → Pages** → Source: `Deploy from a branch` → chọn nhánh `main`, thư mục `/ (root)` → Save.
4. Vài phút sau trang chạy ở `https://<tên-bạn>.github.io/giapha/`.
5. Trỏ `gpphamdinh.balienket.com` sang đó (CNAME trên Cloudflare) thay cho redirect MyHeritage.

## Nút "Xem sơ đồ cây"

Mở Topola Viewer với chính file `giapha.ged` của bạn. URL có tham số `&handleCors=false`
— **bắt buộc phải có**.

Mặc định Topola định tuyến file qua một CORS proxy công cộng, và proxy đó đang chết
→ báo lỗi "Failed to fetch". Tham số này bảo Topola gọi thẳng file. GitHub Pages tự
gửi header CORS nên chạy được.

Nếu sau này muốn hết lệ thuộc vào `pewu.github.io`, có thể tự host Topola trong repo:
tải https://github.com/PeWu/topola-viewer/archive/refs/heads/gh-pages.zip, giải nén vào
thư mục `topola/`, rồi sửa link trong `index.html` trỏ vào đó. Cùng tên miền → CORS
biến mất hoàn toàn.

## Cập nhật dữ liệu

Xuất GEDCOM mới từ MyHeritage, chép vào thư mục này, rồi:

### Windows — lần đầu

Chạy **`ketnoi-github.bat`** một lần duy nhất. Nó nối thư mục này với repo GitHub của bạn.

Nhập địa chỉ repo khi được hỏi (ví dụ `https://github.com/hungps2/giapha.git`), hoặc
bấm Enter để dùng mặc định. Lần đầu sẽ hiện cửa sổ đăng nhập GitHub — đăng nhập bình thường.

Chạy lại cũng không sao: nếu đã nối rồi, script báo và thoát, không làm gì hết.

### Windows — từ đó về sau

**Kéo thả file `.ged` vào `capnhat.bat`.** Xong. Không cần gõ lệnh.

Hoặc mở CMD tại thư mục này và gõ:
```
capnhat.bat file-moi.ged
```

Cần cài sẵn:
- **Python** — https://www.python.org/downloads/ — lúc cài **NHỚ TICK "Add Python to PATH"**
- **Git** — https://git-scm.com/download/win

### macOS / Linux

```bash
chmod +x capnhat.sh          # chỉ cần làm 1 lần
./capnhat.sh file-moi.ged
```

Cả hai script làm cùng một việc: lọc dữ liệu → kiểm tra an toàn → hỏi xác nhận → push.

### Script tự chặn khi có sự cố

Nó **không push** nếu phát hiện bất kỳ điều nào sau đây:
- Người còn sống bị lộ ngày/tháng sinh
- Có email hoặc địa chỉ trong file
- Có link ảnh MyHeritage
- File hỏng, không đọc được
- Số người giảm hơn 10 so với lần trước (sẽ hỏi lại trước khi tiếp tục)

Mỗi lần chạy, bản cũ được sao lưu vào `.saoluu/` kèm dấu thời gian — luôn quay về được.

### Nếu muốn làm từng bước bằng tay

```bash
python3 convert.py file-moi.ged data.json    # sinh ca hai file da loc
git add data.json giapha.ged
git commit -m "Cập nhật gia phả"
git push
```

Đừng sửa tay file GEDCOM hay JSON — sai một ký tự là hỏng cả file.

## `.gitignore` — lớp bảo vệ khỏi sai sót

Repo có sẵn file `.gitignore` với nội dung:

```
*.ged
!giapha.ged
.saoluu/
```

Nghĩa là: kể cả bạn lỡ copy file GEDCOM gốc từ MyHeritage vào thư mục repo, `git` cũng
sẽ **không** đẩy nó lên. Chỉ `giapha.ged` (bản đã lọc) được phép qua.

## RIÊNG TƯ — điều quan trọng nhất

**Người còn sống chỉ hiện NĂM sinh. Ngày và tháng bị cắt ngay từ lúc xuất.**

Cắt lúc xuất, không phải lúc hiển thị. Nghĩa là ngày/tháng sinh của 112 người còn sống
**không tồn tại trong `data.json`**. Ai mở thẳng file JSON, xem mã nguồn trang, hay tải
file về cũng không lấy được — vì dữ liệu đó chưa bao giờ rời khỏi máy bạn.

Đây là cách phân quyền duy nhất có thật trên trang tĩnh. Mọi cách khác (ẩn bằng CSS,
lọc bằng JavaScript, đặt mật khẩu trong mã) chỉ là màn che: dữ liệu vẫn đã tải về
máy người xem rồi.

Người đã mất giữ nguyên ngày tháng đầy đủ — cần cho giỗ chạp.

### Cả HAI file đều đã lọc

`convert.py` sinh ra hai file, và cả hai đều sạch:

| | `data.json` | `giapha.ged` |
|---|---|---|
| Dùng cho | trang chính | nút "Xem sơ đồ cây" (Topola) |
| Ngày/tháng sinh người còn sống | đã cắt | đã cắt |
| Cờ `DEAT Y` giả | đã bỏ | đã bỏ |
| Email, địa chỉ | không có | không có |
| Link ảnh MyHeritage | không có | không có |

**KHÔNG bao giờ đẩy file GEDCOM gốc từ MyHeritage lên GitHub.** Bản gốc chứa đầy đủ
ngày/tháng sinh của 112 người còn sống, email, và địa chỉ. Chỉ đẩy `giapha.ged` do
`convert.py` sinh ra.

## Bốn việc đã xử lý trong lúc chuyển đổi
1. **Cờ mất**: bạn tick "đã mất" cho cả 159 người để MyHeritage đừng ẩn người sống.
   Trên trang này không còn cơ chế ẩn đó, nên bộ chuyển đọc lại đúng: chỉ coi là đã mất
   khi có ngày mất thật → 47 đã mất, 112 còn sống.
2. **Riêng tư**: 34 người còn sống có ngày/tháng đầy đủ → cắt còn năm (xem mục trên).
3. **Đời của dâu/rể**: các bà dâu không có cha mẹ trong cây nên dễ bị xếp nhầm vào đời 1.
   Bộ chuyển tách huyết thống (137) và dâu/rể (22); dâu/rể lấy đời theo chồng/vợ.
4. **Ngày tháng**: `16 APR 1995` → `16/4/1995`.

## Về cách nhập tên
Bạn điền tên đầy đủ vào trường tên, để trống trường họ — đúng, vì GEDCOM là chuẩn
phương Tây (họ đứng sau). Bộ chuyển giữ nguyên tên đầy đủ.

Có vài bản ghi lẻ nhập theo kiểu cũ (`THỊ CÁT /NGUYỄN/`); bộ chuyển tự ghép lại thành
`NGUYỄN THỊ CÁT` cho đúng thứ tự Việt. Nếu muốn nhất quán, sửa mấy bản ghi đó trong
MyHeritage cho khớp phần còn lại.

## Ảnh
46 ảnh trong GEDCOM chỉ là **đường dẫn tới máy chủ MyHeritage**, có chữ ký hết hạn —
không tải về được từ file này. Muốn có ảnh: tải riêng từ MyHeritage, đặt vào thư mục
`anh/`, rồi bổ sung tên file vào `data.json`. Chưa làm ở bản này.
