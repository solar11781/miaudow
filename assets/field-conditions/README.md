# MIAUDOW — Ảnh minh họa chọn loại ruộng

Bộ ảnh dành cho bước **"Ruộng nhà mình thế nào?"** (Step 1/4) của trải nghiệm nông dân.

## 5 lựa chọn tương ứng UI

1. `high-field-hard-to-water` — Ruộng cao, khó lấy nước — minh họa máy bơm nâng nước từ mương thấp lên ruộng cao.
2. `field-at-end-of-canal` — Ruộng cuối kênh — mương nhỏ, dòng nước yếu cuối tuyến.
3. `field-often-short-of-water` — Ruộng hay thiếu nước — lúa bị stress nước, đất khô nứt.
4. `water-under-control` — Chủ động nước — cống/mương đưa nước vào ruộng lúa xanh.
5. `ask-extension-officer` — Chưa rõ, hỏi cán bộ khuyến nông — cán bộ và người dân thảo luận trên đồng.

Ảnh thứ 6 `bonus-irrigation-canal` là cảnh bổ sung cho storytelling, không phải lựa chọn thứ 6.

## Các thư mục

- `web/public/images/field-conditions/cards/*.webp` — ảnh 4:3, tối ưu cho choice card.
- `web/public/images/field-conditions/cards/*.jpg` — fallback JPG.
- `web/public/images/field-conditions/wide/*.webp` — ảnh panorama cho hero / section.
- `web/public/images/field-conditions/thumbnails/*.webp` — ảnh nhẹ 240 × 180 cho danh sách.
- `manifest.json` — ánh xạ option ↔ file + text và metadata.
- `previews/MIAUDOW_Field_Contact_Sheet.jpg` — bảng xem nhanh cả 6 ảnh.

## React + Vite

Copy thư mục `web/public/images/field-conditions` vào `web/public/images/field-conditions` trong repo của bạn. Ví dụ:

```tsx
<img
  src="/images/field-conditions/cards/high-field-hard-to-water.webp"
  alt="Máy bơm đưa nước từ mương thấp lên ruộng cao"
  loading="lazy"
  decoding="async"
  style={{ width: 96, height: 72, objectFit: 'cover', borderRadius: 12 }}
/>
```

Ảnh hỗ trợ nhận diện lựa chọn, nhưng luôn cần nhãn chữ đầy đủ và trạng thái chọn rõ ràng (không dùng ảnh làm dữ liệu khoa học).

## Ghi chú quan trọng

Đây là **ảnh minh họa photorealistic được tạo bằng AI**, dựa trên bối cảnh thủy lợi và đồng lúa miền Trung Việt Nam. **Không phải ảnh tư liệu chụp thực tế tại Đô Lương/Nghệ An**. Không gắn ngày, tọa độ, tên ruộng hoặc nhãn “ảnh thực địa” cho các ảnh này.

Mục đích sử dụng: minh họa UI/UX, không phải bằng chứng thực địa hay cơ sở để ra quyết định nông học.
