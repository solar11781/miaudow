# Reference data sources

`admin_units.csv`: historical NSO provincial units (as named in the NSO English exports) and their status after the
2025 restructuring. Researched 2026-11-11 from sources read directly:

| source_id | Document | URL |
|---|---|---|
| res202_2025_qh15 | Resolution 202/2025/QH15 (adopted 2025-06-12, effective on adoption; new provincial governments operate from 2025-07-01), full text via LuatVietnam | https://luatvietnam.vn/hanh-chinh/nghi-quyet-202-2025-qh15-cua-quoc-hoi-ve-viec-sap-xep-don-vi-hanh-chinh-cap-tinh-402728-d1.html |
| nghean_portal_res202 | Nghệ An provincial portal reproduction of Article 1 clauses 2-23 (Article 1 has 23 clauses) (source: Chinhphu.vn) | https://hcc.nghean.gov.vn/tin-tong-hop/quoc-hoi-thong-qua-nghi-quyet-sap-xep-don-vi-hanh-chinh-cap-tinh-2291.html |
| hatinh_portal_res202 | Hà Tĩnh provincial portal summary of all 23 merger clauses (used for clause 1: Hà Giang + Tuyên Quang) | https://hatinh.gov.vn/vi/bai-viet/quoc-hoi-chinh-thuc-chot-ca-nuoc-con-34-tinh-thanh-pho |
| res15_2008_qh12 | Resolution 15/2008/QH12 (Hà Tây into Hà Nội, effective 2008-08-01), full text via LuatVietnam | https://luatvietnam.vn/dia-gioi-hanh-chinh/nghi-quyet-15-2008-qh12-dieu-chinh-dia-gioi-hanh-chinh-tp-ha-noi-268858-d1.html |
| res175_2024_qh15 | Resolution 175/2024/QH15 (Thừa Thiên Huế becomes thành phố Huế, same area, effective 2025-01-01) | https://luatvietnam.vn/co-cau-to-chuc/nghi-quyet-175-2024-qh15-cua-quoc-hoi-ve-viec-thanh-lap-thanh-pho-hue-truc-thuoc-trung-uong-377830-d1.html |

Status: all 64 rows (63 units plus Hà Tây, merged 2008) confirmed by the sources above; 34 units after 2025 (23 newly formed: 19 provinces and 4 cities; 11 unchanged); 52 merged in 2025, 11 unchanged, 1 merged in 2008. All 2025 mergers are of whole
provinces. Nghệ An, Hà Tĩnh and Thanh Hóa are unchanged.

OPEN (not verified): earlier splits inside the 1995-2024 NSO period (believed around 2004: Đắk Nông, Điện Biên, Hậu Giang)
and how NSO back-cast pre-split and pre-2008 rows. `valid_from_year` is left empty until verified.
