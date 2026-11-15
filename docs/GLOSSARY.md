# Glossary

This glossary explains the farm, data and ML terms used in these documents.

| Term | Vietnamese | Plain meaning |
|---|---|---|
| Yield | năng suất | harvest per sown area, e.g. Nghệ An spring rice 2019: 6.62 tonnes per hectare (NSO data) |
| Hectare (ha) / sào | héc-ta / sào | 10,000 m²; 1 sào Trung Bộ = 499.95 m² (Nghị định 86/2012/NĐ-CP Annex VI) |
| Production | sản lượng | total harvest of an area (yield × area) |
| Planted area | diện tích gieo trồng | area sown with a crop in a season or year |
| Growing season | mùa vụ | the months a crop is in the field |
| Winter-spring / summer-autumn crop | vụ Đông Xuân / vụ Hè Thu | the two rice seasons of two-rice land in Nghệ An plans. NSO calls winter-spring rice "spring rice" and summer-autumn rice "autumn rice"; in North Central Vietnam the NSO calendar has winter-spring rice sown Feb-Mar and harvested May-Jun, summer-autumn sown May-Jun and harvested Aug-Sep (R-V05) |
| Winter rice (mùa rice) | vụ Mùa | a third, separate rice season, distinct from winter-spring rice. The NSO tables E06.22-24 call it "winter rice"; reading it as the 10th-month crop is our assumption. In North Central Vietnam the NSO calendar has it sown Jul-Aug and harvested Oct-Nov (R-V05). In Nghệ An it is a mountain-district season "không chủ động được nguồn nước tưới" (irrigation water not under control; R-G23) and mixes paddy and upland rice (R-G22). It is one of the two seasons the model is trained on (spring and winter rice) |
| Bắc Bộ / Trung Bộ / Bắc Trung Bộ | | regions of Vietnam used in official texts: Bắc Bộ is the north, Trung Bộ the centre, and Bắc Trung Bộ (North Central) the northern part of Trung Bộ. Official forecasting practice places all of Nghệ An in Bắc Trung Bộ (NCHMF bulletins, VASS climate-zone entry; R-K01, R-K02), but the hazard articles never name Nghệ An, and TCVN 8641 does not say whether Nghệ An falls under its Trung bộ or Bắc bộ rows |
| Official risk level | cấp độ rủi ro thiên tai | the official level of a natural hazard under QĐ 18/2021 Art. 4.3: at most 5 levels per hazard type, level 1 low risk, level 2 medium, level 3 large, and so on; each article (Art. 44 heavy rain, 47 heat, 48 drought, 53 damaging cold) gives the thresholds for each level (R-A01) |
| Level 1 or higher | | the rule counts as met when the weather reaches level 1 or any higher level; counting level 1 only would leave out the worst events |
| Basic definition vs risk-level rule | | QĐ 18/2021 Art. 5 defines each hazard in one line (heat: daily maximum "vượt quá 35°c", strictly above 35 °C; rét hại: daily mean "dưới 13oc", strictly below 13 °C); our ML features use these. The risk-level articles (Art. 47, 53) start at 35 °C and up to 13 °C with those values included; the labels shown to farmers use these |
| QĐ / TT / NĐ / Art. | Quyết định / Thông tư / Nghị định / Điều | labels of Vietnamese legal documents: QĐ = decision (e.g. QĐ 18/2021/QĐ-TTg on disaster risk levels), TT = circular (e.g. TT 25/2022/TT-BTNMT, which defines rét đậm), NĐ = decree (e.g. Nghị định 86/2012/NĐ-CP on the sào). "Art." is an article (Điều) of such a document; "Art. 5.21" is item 21 of Article 5 |
| Heading | trổ | "The time when the panicle begins to exsert from the boot" (the rice ear starts to come out); "Flowering generally begins upon panicle exsertion or on the following day and is consequently considered synonymous with heading" (R-K17). The Nghĩa Đàn plan gives 25 April - 5 May 2026 for spring rice (R-G01) |
| Seedbed (nursery) | mạ | FAO: "Nursery: from sowing to transplanting; duration approximately one month"; "The nursery is usually 5 - 10% of the size of the total area to be planted" (R-K18). Nghĩa Đàn: seedbeds 5-20 January 2026 (R-G01) |
| Transplanted / direct-seeded rice | cấy / gieo thẳng | FAO: "The seedlings should be transplanted approximately one month after sowing the nursery"; "If the rice is sown directly (broadcast), the two stages combined are called the vegetative stage" (R-K18) (Nghĩa Đàn transplants 21-day seedlings, R-G01). TCVN 8641 gives separate irrigation amounts for the two |
| Broadcast sowing | gieo vãi | no definition was readable in our sources; FAO uses it for rice "sown directly (broadcast)" (R-K18). In Diễn Châu, summer sesame is broadcast into the field before the spring peanut is harvested (R-C04, R-C05) |
| Fallow | bỏ hoang | land left without a crop for a season. P-03 describes local practice as "Lúa - lúa - bỏ hoang" (rice - rice - fallow) |
| Residues | | the plant parts left after harvest, such as stems and leaves (for peanut: the stover). Witcombe and Tiemann 2022: field nitrogen balances "were only positive when residues were spread and incorporated" (left on the field and mixed into the soil) |
| Skill (skill score) | | how much better a model is than a simple reference forecast: skill = 1 - MSE_model / MSE_reference (WMO/WWRP). Skill > 0 means the model beats the reference; 0 means equal; < 0 means worse. ML analogy: relative improvement over a baseline (ML-DESIGN.md §7) |
| Rolling origin | | time-series validation: for each test year t, train only on years before t and predict year t, then move to t + 1 (Hyndman and Athanasopoulos FPP3, R-S18). ML analogy: an expanding-window split; no random K-fold (ML-DESIGN.md §7) |
| MODIS | | NASA satellite land data from the Terra and Aqua satellites; we use only its yearly land-cover map MCD12C1 (0.05 degree, about 5.5 km pixels; R-N02) to find which grid cells are farmland |
| Crop rotation | luân canh | different crops in planned order on the same field |
| Crop structure | cơ cấu cây trồng | which crops in which seasons on a farm |
| Monoculture | độc canh | the same crop repeatedly |
| Inefficient rice land | đất lúa kém hiệu quả | rice land where rice often fails to pay off (e.g. drought-prone) |
| Legume | cây họ đậu | plants like peanut whose root bacteria fix nitrogen from air |
| Nitrogen | đạm (N) | the main plant nutrient in fertilizer |
| Biomass maize | ngô sinh khối | maize harvested green, whole plant, for animal feed |
| Grain maize | ngô hạt | maize harvested for dry kernels (what NSO statistics count) |
| Drought | hạn hán | water shortage for crops over a period |
| Irrigation | thủy lợi / tưới | delivering water to fields by canal or pump |
| Extension officer | cán bộ khuyến nông | government farm advisor |
| Evapotranspiration (ET) | bốc thoát hơi nước | water leaving the field through soil evaporation and plant leaves |
| Reference ET (ET0) | lượng bốc thoát hơi nước tham chiếu | the weather's water "thirst", independent of crop (background only; no app number uses it) |
| Water deficit | thiếu hụt nước | the part of the crop's water need that rain and soil water do not cover (not computed by the app) |
| Yield anomaly | (độ lệch năng suất) | how far actual yield landed from the past-only normal, in % |
| Trend | xu hướng | the slow long-term change of yields seen in the data (causes not studied here) |
| Reanalysis | (tái phân tích) | gap-free gridded weather built by fitting a physics model to observations |
| Trust label | (thông tin nguồn) | facts about a number's source only: study type, place, years, repeated or not, full text read; no grade |
| Official conditions | (điều kiện theo quy định) | heavy rain, heat, drought rain part and damaging cold by the risk-level rules of QĐ 18/2021/QĐ-TTg (TT 25/2022/TT-BTNMT), applied to NASA weather, shown as a share of farmland |
| Farmland share | | the part of Nghệ An's farmland, by MODIS farmland weights, where a rule was met |
| Out-of-sample prediction | | what the model predicted for a year it was not trained on, like a test-set prediction; shown only for 2016-2024 |
| No-weather twin (BNW) | | the same model without the weather columns; we use it to check whether NASA weather adds anything |
