// Earth-observation missions shown in the observatory. Orbit height and inclination are the published nominal values
// of each mission page (source links below); the satellites' positions on screen are ILLUSTRATIVE, never live
// ephemeris. `status` says what MIAUDOW actually uses from the mission, read against data/canonical/catalog.json.
import type { Bilingual } from '../../domain/provenance';

export type MissionStatus = 'ingested' | 'visual' | 'blocked';

export interface Mission {
  id: string;
  name: string;
  agency: string;
  altitudeKm: number;
  inclinationDeg: number;
  color: string;
  observes: Bilingual;
  product: Bilingual;
  resolution: Bilingual;
  coverage: Bilingual;
  why: Bilingual;
  status: MissionStatus;
  statusNote: Bilingual;
  eyesId?: string;
  source: string;
}

export const MISSIONS: Mission[] = [
  {
    id: 'terra',
    name: 'Terra (MODIS)',
    agency: 'NASA',
    altitudeKm: 705,
    inclinationDeg: 98.2,
    color: '#e9bc57',
    observes: {
      vi: 'Màu sắc và độ xanh của mặt đất, mây, nhiệt độ bề mặt',
      en: 'Land colour and greenness, clouds, surface temperature',
    },
    product: { vi: 'MOD13Q1: chỉ số thực vật NDVI 16 ngày', en: 'MOD13Q1: 16-day NDVI vegetation index' },
    resolution: { vi: '250 m', en: '250 m' },
    coverage: { vi: 'Từ năm 2000', en: 'Since 2000' },
    why: {
      vi: 'Cho thấy ruộng xanh lên và được gặt theo mùa, nhiều năm liền.',
      en: 'Shows fields greening and being harvested, season after season, for years.',
    },
    status: 'ingested',
    statusNote: {
      vi: 'Đã nạp: 10 năm NDVI quanh Lưu Sơn (cũ) (2015–2024).',
      en: 'Loaded: ten years of NDVI around former Luu Son (2015–2024).',
    },
    eyesId: 'sc_terra',
    source: 'https://terra.nasa.gov/about',
  },
  {
    id: 'sentinel2',
    name: 'Sentinel-2',
    agency: 'ESA · Copernicus',
    altitudeKm: 786,
    inclinationDeg: 98.62,
    color: '#8fcf8a',
    observes: { vi: 'Phản xạ mặt đất ở 13 dải phổ', en: 'Surface reflectance in 13 spectral bands' },
    product: {
      vi: 'L2A: phản xạ bề mặt đã hiệu chỉnh khí quyển',
      en: 'L2A: atmospherically corrected surface reflectance',
    },
    resolution: { vi: '10–60 m (MIAUDOW dùng lưới 20 m)', en: '10–60 m (MIAUDOW uses a 20 m grid)' },
    coverage: { vi: 'Từ 2015, khoảng 5 ngày một lần', en: 'Since 2015, about every 5 days' },
    why: {
      vi: 'Đủ mịn để thấy từng vùng ruộng trong một huyện.',
      en: 'Fine enough to see patches of fields inside one district.',
    },
    status: 'ingested',
    statusNote: {
      vi: 'Đã nạp: 59 cảnh trên huyện Đô Lương (cũ), 6 ảnh NDVI theo mùa. Vệ tinh của châu Âu, không phải của NASA.',
      en: 'Loaded: 59 scenes over the former Do Luong district, 6 seasonal NDVI composites. A European satellite, not a NASA one.',
    },
    source: 'https://sentiwiki.copernicus.eu/web/s2-mission',
  },
  {
    id: 'landsat9',
    name: 'Landsat 9',
    agency: 'NASA · USGS',
    altitudeKm: 705,
    inclinationDeg: 98.2,
    color: '#d9a46b',
    observes: { vi: 'Phản xạ và nhiệt độ mặt đất', en: 'Land reflectance and surface temperature' },
    product: { vi: 'HLS: ảnh Landsat và Sentinel-2 hài hòa', en: 'HLS: harmonized Landsat and Sentinel-2' },
    resolution: { vi: '30 m', en: '30 m' },
    coverage: { vi: 'Landsat từ 1972; HLS từ 2013', en: 'Landsat since 1972; HLS since 2013' },
    why: {
      vi: 'Chuỗi ảnh dài nhất để so sánh ruộng qua nhiều thập kỷ.',
      en: 'The longest image record for comparing fields over decades.',
    },
    status: 'blocked',
    statusNote: {
      vi: 'Tìm thấy 319 cảnh HLS trên Đô Lương 2020–2021, nhưng tải về cần tài khoản Earthdata.',
      en: '319 HLS scenes over Do Luong found for 2020–2021, but downloading needs an Earthdata login.',
    },
    eyesId: 'sc_landsat_9',
    source: 'https://landsat.gsfc.nasa.gov/satellites/landsat-9/',
  },
  {
    id: 'smap',
    name: 'SMAP',
    agency: 'NASA',
    altitudeKm: 685,
    inclinationDeg: 98.1,
    color: '#7db7de',
    observes: { vi: 'Độ ẩm lớp đất mặt (khoảng 5 cm)', en: 'Moisture of the top soil (about 5 cm)' },
    product: { vi: 'SPL3SMP_E, SPL4SMGP', en: 'SPL3SMP_E, SPL4SMGP' },
    resolution: { vi: '9 km', en: '9 km' },
    coverage: { vi: 'Từ 2015', en: 'Since 2015' },
    why: {
      vi: 'Cho biết đất khô hay ẩm trên cả vùng, rất thô so với một thửa ruộng.',
      en: 'Shows whether soil is dry or moist across a region; very coarse for one field.',
    },
    status: 'visual',
    statusNote: {
      vi: 'Số liệu cần tài khoản Earthdata; chỉ xem được lớp ảnh trực quan từ NASA GIBS.',
      en: 'The data need an Earthdata login; only the NASA GIBS picture layer can be viewed.',
    },
    eyesId: 'sc_smap',
    source: 'https://smap.jpl.nasa.gov/mission/',
  },
  {
    id: 'gpm',
    name: 'GPM Core Observatory',
    agency: 'NASA · JAXA',
    altitudeKm: 407,
    inclinationDeg: 65,
    color: '#5aa0d6',
    observes: {
      vi: 'Mưa và tuyết, ghép từ nhiều vệ tinh (IMERG)',
      en: 'Rain and snow, merged from many satellites (IMERG)',
    },
    product: { vi: 'IMERG ngày và tháng', en: 'IMERG daily and monthly' },
    resolution: { vi: '0,1° (khoảng 11 km)', en: '0.1° (about 11 km)' },
    coverage: { vi: 'Từ 2000', en: 'Since 2000' },
    why: {
      vi: 'Một nguồn mưa thứ ba để đối chiếu với NASA POWER và CHIRPS.',
      en: 'A third rain source to compare with NASA POWER and CHIRPS.',
    },
    status: 'visual',
    statusNote: {
      vi: 'Số liệu cần tài khoản Earthdata; chỉ xem được lớp ảnh trực quan từ NASA GIBS.',
      en: 'The data need an Earthdata login; only the NASA GIBS picture layer can be viewed.',
    },
    eyesId: 'sc_gpm',
    source: 'https://gpm.nasa.gov/missions/GPM/core-observatory',
  },
  {
    id: 'ecostress',
    name: 'ECOSTRESS (ISS)',
    agency: 'NASA JPL',
    altitudeKm: 415,
    inclinationDeg: 51.6,
    color: '#ee8e70',
    observes: {
      vi: 'Nhiệt độ bề mặt và lượng nước cây thoát ra',
      en: 'Surface temperature and water given off by plants',
    },
    product: { vi: 'ECO_L2T_LSTE, ECO_L3T_JET', en: 'ECO_L2T_LSTE, ECO_L3T_JET' },
    resolution: { vi: '70 m', en: '70 m' },
    coverage: { vi: 'Từ 2018, giờ bay không cố định', en: 'Since 2018, at varying times of day' },
    why: {
      vi: 'Cây thiếu nước nóng hơn cây đủ nước; có thể giúp thấy ruộng khô.',
      en: 'Water-stressed plants run warmer; it can help spot dry fields.',
    },
    status: 'blocked',
    statusNote: {
      vi: 'Tìm thấy 276 tệp trên Đô Lương 2020–2021, nhưng tải về cần tài khoản Earthdata.',
      en: '276 files over Do Luong found for 2020–2021, but downloading needs an Earthdata login.',
    },
    eyesId: 'sc_iss_ecostress',
    source: 'https://ecostress.jpl.nasa.gov/',
  },
];
