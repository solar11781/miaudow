import type { SourceId, SourceRecord } from './provenance';

// The source registry. Text here describes the sources; it adds no new findings.
export const SOURCES: Record<SourceId, SourceRecord> = {
  p02: {
    id: 'p02',
    registerId: 'R-P02',
    kind: 'study',
    short: 'Trịnh Đức Toàn và cs. 2023 · VAAS',
    title: {
      vi: 'Kết quả thử nghiệm một số cây trồng trên đất lúa kém hiệu quả, thường xuyên khô hạn tại tỉnh Nghệ An',
      en: 'Testing of some crops on ineffective, frequently drought-affected rice land in Nghệ An province',
    },
    publisher: {
      vi: 'Trịnh Đức Toàn và cộng sự (2023), Tạp chí Khoa học và Công nghệ Nông nghiệp Việt Nam, số 04(146), tr. 43–51',
      en: 'Trịnh Đức Toàn et al. (2023), Vietnam Journal of Agricultural Science and Technology, 04(146), pp. 43–51',
    },
    where: { vi: 'Xã Lưu Sơn, huyện Đô Lương (cũ), Nghệ An', en: 'Lưu Sơn commune, former Đô Lương district, Nghệ An' },
    period: { vi: 'Tháng 6/2020 – tháng 6/2021', en: 'June 2020 – June 2021' },
    method: {
      vi: 'Thử nghiệm đồng ruộng, mỗi cây một ô 1.000 m², không lặp lại; lãi đã trừ công lao động (Bảng 13)',
      en: 'Field trial, one 1,000 m² plot per crop, not replicated; profit net of labour (Table 13)',
    },
    howRead: {
      vi: 'Đã đọc toàn văn; ngày gieo và thu hoạch lấy từ Bảng 1, 5, 9',
      en: 'Full text read; sowing and harvest dates from Tables 1, 5 and 9',
    },
    caveat: {
      vi: 'Một năm, một ô cho mỗi cây. Bài không nói cả chuỗi ba vụ có trồng liền trên một ruộng hay không; hai chỗ ngày tháng chồng nhau.',
      en: 'One year and one plot per crop. The paper does not say whether one field carried each whole sequence; two reported dates overlap.',
    },
    url: 'https://tapchi.vaas.vn/vi/tap-chi/ket-qua-thu-nghiem-mot-so-cay-trong-tren-dat-lua-kem-hieu-qua-thuong-xuyen-kho-han-tai-tinh',
  },
  p03: {
    id: 'p03',
    registerId: 'R-P03',
    kind: 'study',
    short: 'Trịnh Đức Toàn và cs. 2023 · KH&CN Nghệ An',
    title: {
      vi: 'Thử nghiệm một số công thức luân canh trên đất lúa kém hiệu quả, có nguy cơ thiếu nước tại tỉnh Nghệ An',
      en: 'Testing some rotation formulas on inefficient, water-short rice land in Nghệ An province',
    },
    publisher: {
      vi: 'Trịnh Đức Toàn và cộng sự (2023), Đặc san KH&CN Nghệ An, số 2/2023',
      en: 'Trịnh Đức Toàn et al. (2023), Nghệ An Science & Technology special issue 2/2023',
    },
    where: { vi: 'Xã Lưu Sơn, Đô Lương, Nghệ An', en: 'Lưu Sơn commune, Đô Lương, Nghệ An' },
    period: { vi: 'Tháng 6/2020 – tháng 6/2021', en: 'June 2020 – June 2021' },
    method: {
      vi: 'Mô hình trình diễn, không lặp lại; cách tính lãi khác P-02',
      en: 'Demonstration plots, not replicated; profit defined differently from P-02',
    },
    howRead: { vi: 'Đã đọc toàn văn bản PDF do nhóm cung cấp', en: 'Full text read from the PDF supplied by the team' },
    caveat: {
      vi: 'Cùng xã với P-02 nhưng mô tả cách làm hiện nay khác: “Lúa – lúa – bỏ hoang”. Bài không ghi ngày gieo nên không tính được thời tiết theo cây.',
      en: 'Same site as P-02 but describes current practice differently: “rice – rice – fallow”. It gives no sowing dates, so weather per crop cannot be computed.',
    },
  },
  qd18: {
    id: 'qd18',
    registerId: 'R-A01',
    kind: 'standard',
    short: 'QĐ 18/2021/QĐ-TTg',
    title: {
      vi: 'Quyết định 18/2021/QĐ-TTg quy định về dự báo, cảnh báo, truyền tin thiên tai và cấp độ rủi ro thiên tai',
      en: 'Prime Minister’s Decision 18/2021 on disaster forecasting, warning and risk levels',
    },
    publisher: { vi: 'Thủ tướng Chính phủ', en: 'Prime Minister of Vietnam' },
    where: {
      vi: 'Toàn quốc; áp dụng cách viết cho Bắc Trung Bộ',
      en: 'Nationwide; the North Central wording is applied',
    },
    period: { vi: 'Ban hành năm 2021', en: 'Issued 2021' },
    method: {
      vi: 'Ngưỡng cấp độ rủi ro: mưa lớn Điều 44, nắng nóng Điều 47, hạn (phần mưa) Điều 48, rét hại Điều 53',
      en: 'Risk-level thresholds: heavy rain Art. 44, heat Art. 47, drought rain part Art. 48, damaging cold Art. 53',
    },
    howRead: {
      vi: 'Đã đọc nguyên văn; Miaudow áp ngưỡng từ cấp độ 1 trở lên',
      en: 'Read verbatim; Miaudow applies the thresholds at level 1 or higher',
    },
    caveat: {
      vi: 'Cảnh báo chính thức còn xét thêm độ ẩm, gió và thời gian. Đây là cách đọc máy móc các bảng của Quyết định, không phải số liệu chính thức.',
      en: 'Official warnings also weigh humidity, wind and duration. This is a mechanical reading of the decree’s tables, not an official record.',
    },
    url: 'https://vupc.mae.gov.vn/Data/files/18_2021_QD-TTg.doc',
  },
  tcvn8641: {
    id: 'tcvn8641',
    registerId: 'R-W15',
    kind: 'standard',
    short: 'TCVN 8641:2011',
    title: {
      vi: 'TCVN 8641:2011 Công trình thủy lợi – Kỹ thuật tưới tiêu nước cho cây lương thực và cây thực phẩm',
      en: 'TCVN 8641:2011 Irrigation techniques for food crops',
    },
    publisher: { vi: 'Bộ Khoa học và Công nghệ', en: 'Ministry of Science and Technology' },
    where: { vi: 'Việt Nam, theo vùng', en: 'Vietnam, by region' },
    period: { vi: 'Năm 2011', en: '2011' },
    method: {
      vi: 'Mức tưới cả vụ (m³/ha); với lúa chỉ tính tưới dưỡng, không tính làm đất',
      en: 'Seasonal irrigation amount (m³/ha); for rice, maintenance only, land preparation excluded',
    },
    howRead: { vi: 'Đọc qua bản đăng trên caselaw.vn', en: 'Read via the caselaw.vn copy' },
    caveat: {
      vi: 'Tiêu chuẩn không nói Nghệ An thuộc Trung bộ hay Bắc bộ. 1 m³/ha bằng 0,1 mm nước trên ruộng.',
      en: 'The standard does not say whether Nghệ An belongs to the central or northern region. 1 m³/ha equals 0.1 mm of water.',
    },
  },
  'fao-tm3': {
    id: 'fao-tm3',
    registerId: 'R-M02',
    kind: 'standard',
    short: 'FAO Training Manual 3',
    title: {
      vi: 'FAO Irrigation Water Management, Training Manual 3, Bảng 14',
      en: 'FAO Irrigation Water Management, Training Manual 3, Table 14',
    },
    publisher: {
      vi: 'Tổ chức Lương thực và Nông nghiệp Liên Hợp Quốc (FAO)',
      en: 'Food and Agriculture Organization of the UN (FAO)',
    },
    where: { vi: 'Toàn cầu', en: 'Global' },
    period: { vi: 'Tài liệu hướng dẫn', en: 'Training manual' },
    method: { vi: 'Nhu cầu nước cả vụ theo FAO, “ước tính thô”', en: 'Seasonal crop water need, a “rough estimate”' },
    howRead: { vi: 'Đã đọc', en: 'Read' },
    caveat: {
      vi: 'Không dành riêng cho Nghệ An; chỉ hiện cho cây có trong bảng.',
      en: 'Not specific to Nghệ An; shown only for crops the table lists.',
    },
  },
  'nasa-power': {
    id: 'nasa-power',
    registerId: 'R-N01',
    kind: 'data',
    short: 'NASA POWER',
    title: {
      vi: 'NASA POWER – thời tiết theo ngày (API Daily, cộng đồng AG)',
      en: 'NASA POWER daily weather (Daily API, AG community)',
    },
    publisher: { vi: 'Trung tâm Nghiên cứu Langley của NASA', en: 'NASA Langley Research Center' },
    where: {
      vi: '5 ô lưới phủ đất trồng Nghệ An, mỗi ô 0,5° × 0,625° (khoảng 50 km)',
      en: '5 grid cells over Nghệ An farmland, each 0.5° × 0.625° (about 50 km)',
    },
    period: { vi: '1990–2024, theo ngày', en: '1990–2024, daily' },
    method: {
      vi: 'Dữ liệu tái phân tích: mô hình vật lý khớp với vệ tinh và trạm đo (MERRA-2)',
      en: 'Reanalysis: a physics model fitted to satellites and stations (MERRA-2)',
    },
    howRead: {
      vi: 'Tải trực tiếp từ API ngày 14/11/2026; không điền giá trị thiếu',
      en: 'Downloaded from the API on 14 Nov 2026; no missing value filled',
    },
    caveat: {
      vi: 'Ô lưới 50 km làm mượt các đợt cực đoan; ruộng nhà bạn không được đo trực tiếp.',
      en: '50 km cells smooth out extremes; your own field is not measured.',
    },
    url: 'https://power.larc.nasa.gov/',
    licence: { vi: 'Dữ liệu mở của NASA, cần trích dẫn', en: 'NASA open data, citation requested' },
  },
  'chirps-v3': {
    id: 'chirps-v3',
    registerId: 'R-D05',
    kind: 'data',
    short: 'CHIRPS v3',
    title: {
      vi: 'CHIRPS v3 – lượng mưa tháng (vệ tinh kết hợp trạm đo)',
      en: 'CHIRPS v3 monthly rainfall (satellite and station blend)',
    },
    publisher: {
      vi: 'Climate Hazards Center, Đại học California Santa Barbara',
      en: 'Climate Hazards Center, UC Santa Barbara',
    },
    where: {
      vi: 'Các điểm ảnh 0,05° thuộc Nghệ An trong 5 ô lưới NASA POWER, và điểm ảnh ở Lưu Sơn',
      en: 'The 0.05° Nghệ An pixels inside the 5 NASA POWER cells, and the Lưu Sơn pixel',
    },
    period: {
      vi: '1991–2024, theo tháng, bản cuối (không dùng bản sơ bộ)',
      en: '1991–2024, monthly, final product (never preliminary)',
    },
    method: {
      vi: 'Ước lượng mưa từ vệ tinh hồng ngoại, hiệu chỉnh bằng trạm đo',
      en: 'Infrared satellite rainfall estimates calibrated with station data',
    },
    howRead: {
      vi: 'Đọc từng tháng qua HTTP theo vùng nhỏ, ngày 14/11/2026; không điền giá trị thiếu',
      en: 'Read month by month over HTTP for a small window on 14 Nov 2026; nothing filled',
    },
    caveat: {
      vi: 'Lưới 0,05° (khoảng 5 km) vẫn lớn hơn một thửa ruộng; không trộn với NASA POWER.',
      en: 'A 0.05° grid (about 5 km) is still larger than a field; never merged with NASA POWER.',
    },
    url: 'https://www.chc.ucsb.edu/data/chirps3',
    licence: {
      vi: 'CC BY 4.0 (đã từ bỏ bản quyền), cần trích dẫn',
      en: 'CC BY 4.0 (copyright waived), citation requested',
    },
  },
  'modis-ndvi': {
    id: 'modis-ndvi',
    registerId: 'R-N11',
    kind: 'data',
    short: 'NASA MODIS MOD13Q1',
    title: {
      vi: 'MODIS MOD13Q1 v061 – chỉ số thực vật NDVI 16 ngày, 250 m',
      en: 'MODIS MOD13Q1 v061 – 16-day NDVI, 250 m',
    },
    publisher: {
      vi: 'NASA LP DAAC; trích xuất qua công cụ ORNL DAAC',
      en: 'NASA LP DAAC; subset through the ORNL DAAC tool',
    },
    where: {
      vi: '81 điểm ảnh 250 m quanh xã Lưu Sơn (cũ), Đô Lương',
      en: '81 pixels of 250 m around former Lưu Sơn commune, Đô Lương',
    },
    period: { vi: '2015–2024, 16 ngày một lần', en: '2015–2024, every 16 days' },
    method: {
      vi: 'Trung vị các điểm ảnh tin cậy; điểm ảnh có mây bị loại',
      en: 'Median of reliable pixels; cloudy pixels excluded',
    },
    howRead: { vi: 'Tải qua API ORNL ngày 14/11/2026', en: 'Downloaded through the ORNL API on 14 Nov 2026' },
    caveat: {
      vi: 'Độ xanh không phải năng suất hay sâu bệnh; một điểm ảnh gồm nhiều thửa.',
      en: 'Greenness is not yield or pests; one pixel mixes several fields.',
    },
    url: 'https://doi.org/10.5067/MODIS/MOD13Q1.061',
    licence: { vi: 'Dữ liệu mở của NASA', en: 'NASA open data' },
  },
  modis: {
    id: 'modis',
    registerId: 'R-N02',
    kind: 'data',
    short: 'NASA MODIS MCD12C1',
    title: {
      vi: 'MODIS Land Cover MCD12C1 v061 – trọng số đất trồng',
      en: 'MODIS Land Cover MCD12C1 v061 – farmland weights',
    },
    publisher: {
      vi: 'Friedl và Sulla-Menashe (2022), NASA LP DAAC',
      en: 'Friedl and Sulla-Menashe (2022), NASA LP DAAC',
    },
    where: { vi: 'Các ô lưới NASA POWER trong Nghệ An', en: 'NASA POWER cells in Nghệ An' },
    period: { vi: 'Một bản đồ cố định trước năm 2016', en: 'One fixed map before 2016' },
    method: {
      vi: 'Phần đất trồng trong mỗi ô, dùng làm trọng số',
      en: 'Farmland share of each cell, used as a weight',
    },
    howRead: { vi: 'Tính trong quy trình dữ liệu của nhóm', en: 'Computed in the team’s data pipeline' },
    caveat: {
      vi: 'Ô miền núi phía tây có trọng số 0 nên không được dùng.',
      en: 'Western mountain cells have zero weight and are not used.',
    },
    url: 'https://doi.org/10.5067/MODIS/MCD12C1.061',
    licence: { vi: 'CC0', en: 'CC0' },
  },
  nso: {
    id: 'nso',
    registerId: 'R-D01',
    kind: 'data',
    short: 'Cục Thống kê',
    title: { vi: 'Năng suất lúa theo tỉnh và vụ, 1995–2024', en: 'Rice yield by province and season, 1995–2024' },
    publisher: { vi: 'Cục Thống kê (www.gso.gov.vn)', en: 'National Statistics Office of Vietnam (www.gso.gov.vn)' },
    where: { vi: 'Toàn tỉnh Nghệ An, trung bình cả tỉnh', en: 'Province average for Nghệ An' },
    period: { vi: '1995–2024', en: '1995–2024' },
    method: {
      vi: 'Mức lệch = năng suất thật ÷ mức bình thường − 1; mức bình thường là trung bình 3 năm trước (E-010)',
      en: 'Anomaly = actual yield ÷ normal − 1; the normal is the mean of the 3 previous years (E-010)',
    },
    howRead: { vi: 'Bảng E06 trên PX-Web', en: 'Tables E06 on PX-Web' },
    caveat: {
      vi: 'Trung bình cả tỉnh, phần lớn là lúa có tưới; không phải năng suất ruộng nhà bạn. Số liệu không nói vì sao một năm thấp.',
      en: 'A province average, mostly irrigated rice; not your field’s yield. The statistics do not say why a year was low.',
    },
    url: 'https://pxweb.nso.gov.vn/pxweb/en/',
    licence: { vi: 'Nguồn: trang Thông tin điện tử Cục Thống kê', en: 'Source: NSO website' },
  },
  geoboundaries: {
    id: 'geoboundaries',
    registerId: 'R-D04',
    kind: 'data',
    short: 'geoBoundaries',
    title: {
      vi: 'Ranh giới tỉnh Việt Nam (geoBoundaries gbOpen VNM ADM1)',
      en: 'Vietnam province boundaries (geoBoundaries gbOpen VNM ADM1)',
    },
    publisher: { vi: 'Phòng thí nghiệm geoLab, William & Mary', en: 'geoLab, William & Mary' },
    where: { vi: 'Ranh giới Nghệ An, đã làm đơn giản', en: 'Nghệ An outline, simplified' },
    period: { vi: 'Bản phát hành 9469f09', en: 'Release 9469f09' },
    method: { vi: 'Đường viền tỉnh dùng để vẽ bản đồ', en: 'Province outline used to draw the map' },
    howRead: { vi: 'Tải theo địa chỉ và mã băm đã ghi', en: 'Fetched by recorded URL and checksum' },
    caveat: {
      vi: 'Ranh giới trước sắp xếp năm 2025; đã làm đơn giản để vẽ.',
      en: 'Boundary before the 2025 reform; simplified for drawing.',
    },
    licence: { vi: 'Phạm vi công cộng theo siêu dữ liệu', en: 'Public domain per its metadata' },
  },
  e012: {
    id: 'e012',
    registerId: 'E-012',
    kind: 'model',
    short: 'E-012 · bài kiểm tra chính',
    title: {
      vi: 'Bài kiểm tra chính E-012: mô hình M1 ridge, kiểm tra trên các năm 2016–2024',
      en: 'Primary test E-012: M1 ridge model, tested on 2016–2024',
    },
    publisher: { vi: 'Nhóm Miaudow, đóng băng ở commit ea7a60c', en: 'Team Miaudow, frozen at commit ea7a60c' },
    where: { vi: 'Cả nước; riêng Nghệ An, Hà Tĩnh, Thanh Hóa', en: 'Nationwide; Nghệ An, Hà Tĩnh, Thanh Hóa subset' },
    period: { vi: 'Năm kiểm tra 2016–2024 (gốc lăn)', en: 'Test years 2016–2024 (rolling origin)' },
    method: {
      vi: 'So với 3 đối thủ: trung bình nhiều năm (B0), giống năm trước (B2), cùng mô hình bỏ thời tiết (BNW); khoảng tin cậy 90% bằng lấy mẫu lại theo năm',
      en: 'Compared with climatology (B0), persistence (B2) and the same model without weather (BNW); 90% intervals by resampling years',
    },
    howRead: {
      vi: 'Kết quả ghi trong metrics.json và gates.json',
      en: 'Results recorded in metrics.json and gates.json',
    },
    caveat: {
      vi: 'Lúa xuân không vượt mô hình bỏ thời tiết, nên dự đoán lúa xuân không được hiện. Lúa mùa vượt qua, với mức hơn nhỏ.',
      en: 'Spring rice did not beat the no-weather model, so spring predictions are not shown. Winter rice passed by a small margin.',
    },
  },
  e010: {
    id: 'e010',
    registerId: 'E-010',
    kind: 'derived',
    short: 'E-010 · mức bình thường',
    title: { vi: 'Cách tính năng suất bình thường (E-010)', en: 'How the normal yield is computed (E-010)' },
    publisher: { vi: 'Nhóm Miaudow', en: 'Team Miaudow' },
    where: { vi: 'Mọi tỉnh và vụ', en: 'All provinces and seasons' },
    period: { vi: 'Chọn trên các năm 2011–2015', en: 'Chosen on 2011–2015' },
    method: {
      vi: 'Trung bình 3 năm trước, chỉ dùng các năm đã qua',
      en: 'Mean of the 3 previous years, past years only',
    },
    howRead: { vi: 'Ghi trong metrics.json', en: 'Recorded in metrics.json' },
    caveat: {
      vi: 'Ba năm đầu chưa có mức bình thường nên không có mức lệch.',
      en: 'The first three years have no normal, so no anomaly.',
    },
  },
  zhang2011: {
    id: 'zhang2011',
    registerId: 'R-A10',
    kind: 'study',
    short: 'Zhang et al. 2011',
    title: {
      vi: 'Chỉ số cực trị khí hậu trên dữ liệu lưới (Zhang và cộng sự, 2011)',
      en: 'Climate extremes indices on gridded data (Zhang et al., 2011)',
    },
    publisher: { vi: 'WIREs Climate Change', en: 'WIREs Climate Change' },
    where: { vi: 'Toàn cầu', en: 'Global' },
    period: { vi: '2011', en: '2011' },
    method: { vi: 'Giá trị lưới làm mượt cực trị', en: 'Gridded values smooth extremes' },
    howRead: { vi: 'Đọc phần tóm tắt', en: 'Abstract read' },
    caveat: { vi: 'Dùng để nói rõ giới hạn, không tạo số mới.', en: 'Used to state a limit, not to make new numbers.' },
  },
};

export const sourceById = (id: SourceId) => SOURCES[id];
