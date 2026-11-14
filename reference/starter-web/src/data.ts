export type View = 'home'|'farmer'|'officer'|'science'|'evidence'|'copilot';
export const images = {
 hero:'/images/d1_horizon_golden.webp',
 aerial:'/images/d2_fields_golden.webp',
 rice:'/images/d3_rice_golden.webp',
 river:'/images/d4_river_golden.webp',
 landscape:'/images/a1_horizon_golden.webp',
 geometry:'/images/a2_fields_golden.webp',
 macro:'/images/a3_rice_golden.webp',
 mist:'/images/b4_river_golden.webp',
};
export const routes: {id:View,label:string,short:string}[]=[
 {id:'home',label:'Trang chủ',short:'Trang chủ'},
 {id:'farmer',label:'Nông dân',short:'Nhà nông'},
 {id:'officer',label:'Cán bộ',short:'Cán bộ'},
 {id:'science',label:'Khoa học',short:'Dữ liệu'},
 {id:'evidence',label:'Bằng chứng',short:'Nguồn'},
 {id:'copilot',label:'Trợ lý',short:'Trợ lý'},
];
export const sources = [
 {id:'nasa-power',name:'NASA POWER',topic:'Khí tượng lịch sử',tag:'Mô hình khí tượng',range:'Theo ngày; độ phân giải tùy biến',url:'https://power.larc.nasa.gov/docs/services/api/temporal/daily/',detail:'Dữ liệu khí tượng từ hệ thống mô hình đồng hóa; không phải trạm đo tại ruộng.',status:'verified-metadata',image:'river'},
 {id:'chirps-v3',name:'CHIRPS v3',topic:'Lượng mưa và hạn',tag:'Vệ tinh + trạm đo',range:'Từ 1981 · lưới 0,05°',url:'https://www.nature.com/articles/s41597-026-07096-4',detail:'Ước lượng mưa trên ô lưới; các đợt mưa địa phương có thể khác.',status:'verified-metadata',image:'geometry'},
 {id:'s2',name:'Copernicus Sentinel-2',topic:'Bề mặt ruộng và cây trồng',tag:'Ảnh đa phổ',range:'Độ phân giải 10/20/60 m tùy kênh',url:'https://documentation.dataspace.copernicus.eu/APIs/SentinelHub/Data/S2L2A.html',detail:'Chỉ số thực vật không tự động chứng minh sâu bệnh hoặc thiếu nước.',status:'verified-metadata',image:'aerial'},
 {id:'hls',name:'NASA HLS',topic:'Theo dõi mùa vụ qua ảnh',tag:'Landsat + Sentinel',range:'Dữ liệu 30 m',url:'https://hls.gsfc.nasa.gov/data-products/',detail:'Quan sát thảm thực vật theo thời gian; cần mặt nạ mây và dữ liệu kiểm chứng.',status:'verified-metadata',image:'rice'},
 {id:'nso',name:'Cục Thống kê Việt Nam',topic:'Năng suất, diện tích, sản lượng',tag:'Thống kê chính thức',range:'Nhiều năm, theo địa phương',url:'https://www.nso.gov.vn/so-lieu-thong-ke/',detail:'Dùng để đối chiếu ở cấp địa phương, không thay thế số đo trên từng thửa ruộng.',status:'verified-metadata',image:'landscape'},
 {id:'trial',name:'Nghiên cứu P-02 / P-03',topic:'Cơ cấu cây trồng được thử nghiệm',tag:'Tài liệu cần xác minh',range:'Tham chiếu trong bản gốc 2020–2021',url:'',detail:'Chưa nạp và kiểm chứng toàn văn trong bộ sản phẩm này; không công bố số lợi nhuận như dữ liệu thực.',status:'pending',image:'macro'},
] as const;
import rotationData from './rotations.generated.json';
export const rotations = rotationData;
