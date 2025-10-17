import geopandas as gpd
import folium
import urllib.parse

# -----------------------------
# 파일 경로
# -----------------------------
buildings_path = r"D:/preprocessing/map/do_buld5.shp"
poi_path = r"D:/preprocessing/POI/yongdu_pois.shp"

# -----------------------------
# 데이터 불러오기
# -----------------------------
buildings = gpd.read_file(buildings_path, encoding='utf-8')
target_bdtp = ["02000", "02001", "02002", "02003"]
buildings = buildings[buildings["BDTYP_CD"].isin(target_bdtp)]
poi_gdf = gpd.read_file(poi_path, encoding='utf-8')

# -----------------------------
# CRS 설정
# -----------------------------
if buildings.crs is None:
    buildings.set_crs(epsg=5179, inplace=True)
if poi_gdf.crs is None:
    poi_gdf.set_crs(epsg=5179, inplace=True)

buildings = buildings.to_crs(epsg=5179)
poi_gdf = poi_gdf.to_crs(epsg=5179)

# -----------------------------
# POI 버퍼 250m → 건축물 선택 (지도용)
# -----------------------------
target_categories = {
    '학교': {'fill': '#a2d2ff', 'line': '#3a7bd5'},
    '어린이집': {'fill': '#b0f2b6', 'line': '#2e8b57'},
    '지하철역': {'fill': '#d8b4ff', 'line': '#7a3fbf'},
    '병원': {'fill': '#ffb3b3', 'line': '#d63434'}
}

buffer_layers = {}

for cat, colors in target_categories.items():
    subset = poi_gdf[poi_gdf["category"] == cat]
    if subset.empty:
        continue

    buffers = subset.buffer(250)
    buffer_union = gpd.GeoDataFrame(geometry=buffers, crs="EPSG:5179")

    # 버퍼 내 건축물 추출
    buildings_in_buffer = gpd.sjoin(buildings, buffer_union, how="inner", predicate="intersects")

    if not buildings_in_buffer.empty:
        buffer_layers[cat] = {
            "gdf": buildings_in_buffer.to_crs(epsg=4326),
            "fill_color": colors['fill'],
            "line_color": colors['line']
        }

# -----------------------------
# 지도용 좌표계
# -----------------------------
buildings = buildings.to_crs(epsg=4326)
poi_gdf = poi_gdf.to_crs(epsg=4326)

# -----------------------------
# 지도 생성
# -----------------------------
center = [buildings.geometry.centroid.y.mean(), buildings.geometry.centroid.x.mean()]
m = folium.Map(location=center, zoom_start=16, tiles="cartodbpositron")

# -----------------------------
# 팝업 HTML 생성 (복사 버튼 + 네이버 부동산 링크)
# -----------------------------
def make_popup_with_copy(name):
    if not name or name.strip() == "":
        name = "알 수 없는 건축물"
    encoded_name = urllib.parse.quote(name)
    naver_link = f"https://new.land.naver.com/search?query={encoded_name}"

    html = f"""
    <div style="font-family:sans-serif; font-size:14px; line-height:1.4;">
        <b>{name}</b>
        <button onclick="navigator.clipboard.writeText('{name}')"
                style="
                    background-color:#d3d3d3;
                    color:black;
                    border:none;
                    padding:2px 6px;
                    border-radius:3px;
                    font-size:12px;
                    margin-left:5px;
                    cursor:pointer;
                ">
            📋 복사
        </button>
        <br>
        <a href="{naver_link}" target="_blank" 
           style="text-decoration:none; color:#1E90FF; font-weight:bold; font-size:13px;">
            🔗 네이버 부동산 보기
        </a>
    </div>
    """
    return html

buildings['popup_html'] = buildings['POS_BUL_NM'].apply(make_popup_with_copy)

# -----------------------------
# 전체 건축물 레이어 (항상 표시)
# -----------------------------
building_layer = folium.FeatureGroup(name="건축물", show=True)
folium.GeoJson(
    buildings,
    style_function=lambda f: {"fillColor":"#F5A623","color":"#555555","weight":0.8,"fillOpacity":0.1},
    tooltip=folium.GeoJsonTooltip(fields=['POS_BUL_NM'], aliases=['건축물명:']),
    popup=folium.GeoJsonPopup(fields=['popup_html'], labels=False)
).add_to(building_layer)
building_layer.add_to(m)

# -----------------------------
# POI 버퍼 내 건축물 레이어 (범례 ON/OFF, 파스텔톤 + 진한 테두리)
# -----------------------------
for cat, info in buffer_layers.items():
    info["gdf"]['popup_html'] = info["gdf"]['POS_BUL_NM'].apply(make_popup_with_copy)
    folium.GeoJson(
        info["gdf"],
        style_function=lambda feature, fc=info["fill_color"], lc=info["line_color"]: {
            "fillColor": fc,
            "color": lc,
            "weight": 1.5,
            "fillOpacity": 0.5
        },
        tooltip=folium.GeoJsonTooltip(fields=['POS_BUL_NM'], aliases=['건축물명:']),
        popup=folium.GeoJsonPopup(fields=['popup_html'], labels=False)
    ).add_to(folium.FeatureGroup(name=f"{cat} 주변 건축물", show=True).add_to(m))
# -----------------------------
# POI 마커 (항상 켜짐 + 카테고리별 아이콘 + 색상)
# -----------------------------
icon_dict = {
    '학교': 'graduation-cap',
    '어린이집': 'child',
    '지하철역': 'subway',
    '병원': 'plus-square'
}

color_dict = {
    '학교': 'blue',
    '어린이집': 'green',
    '지하철역': 'purple',
    '병원': 'red'
}

# FeatureGroup 생성 (항상 켜짐)
layer_groups = {cat: folium.FeatureGroup(name=cat, show=True) for cat in target_categories.keys()}

for _, row in poi_gdf.iterrows():
    cat = row.get('category')
    if cat not in layer_groups:
        continue
    lat, lon = row.geometry.y, row.geometry.x
    place_name = row.get('place_name', '이름없음')
    phone = row.get('phone', '정보없음')
    popup_html = f"<b>{place_name}</b><br>범주: {cat}<br>전화: {phone}"

    folium.Marker(
        location=(lat, lon),
        popup=popup_html,
        icon=folium.Icon(
            icon=icon_dict.get(cat, 'info-sign'),
            prefix='fa',  # FontAwesome 아이콘 사용
            color=color_dict.get(cat, 'blue')  # 기본 Folium 색상
        )
    ).add_to(layer_groups[cat])

for layer in layer_groups.values():
    layer.add_to(m)
# -----------------------------
# Layer Control
# -----------------------------
folium.LayerControl(collapsed=False).add_to(m)

# -----------------------------
# 지도 저장
# -----------------------------
output_path = r"D:/preprocessing/map/yongdu_buildings_final.html"
m.save(output_path)
print(f"✅ 지도 생성 완료: {output_path}")

# folium 지도 저장
output_path = r"D:/preprocessing/map/yongdu_buildings_final.html"
m.save(output_path)

# HTML 열기 & 사용자 선택 인터페이스 추가
with open(output_path, "r", encoding="utf-8") as f:
    html_content = f.read()

# HTML에 선택창 추가 (지도 위에 표시)
custom_ui = """
<div id="overlay" style="
    position: fixed; 
    top: 0; left: 0; 
    width: 100%; height: 100%;
    background: rgba(255,255,255,0.95);
    display: flex;
    flex-direction: column;
    justify-content: center;
    align-items: center;
    z-index: 9999;
">
    <h2 style="font-family:sans-serif;">표시할 범주를 선택하세요</h2>
    <div id="checkboxes" style="margin: 10px; text-align: left;">
        <label><input type="checkbox" value="학교"> 학교</label><br>
        <label><input type="checkbox" value="어린이집"> 어린이집</label><br>
        <label><input type="checkbox" value="지하철역"> 지하철역</label><br>
        <label><input type="checkbox" value="병원"> 병원</label><br>
    </div>
    <button onclick="applySelection()" style="
        padding:10px 20px; 
        font-size:16px; 
        background:#0078d7; 
        color:white; 
        border:none; 
        border-radius:5px;
        cursor:pointer;
    ">지도 보기</button>
</div>

<script>
function applySelection() {
    const checkboxes = document.querySelectorAll('#checkboxes input[type=checkbox]');
    const selected = [];
    checkboxes.forEach(chk => {
        if (chk.checked) selected.push(chk.value);
    });

    if (selected.length === 0) {
        alert('하나 이상 선택해주세요!');
        return;
    }

    // folium에서 만들어진 layer control을 모두 순회
    const layers = document.querySelectorAll('.leaflet-control-layers-selector');
    layers.forEach(layer => {
        const label = layer.nextSibling.textContent.trim();
        const match = selected.some(sel => label.includes(sel));
        layer.checked = match; // 선택된 것만 체크
        layer.dispatchEvent(new Event('click')); // 상태 갱신
    });

    document.getElementById('overlay').style.display = 'none';
}
</script>
"""

# HTML 파일에 선택창 오버레이 추가
html_content = html_content.replace("</body>", custom_ui + "\n</body>")

with open(output_path, "w", encoding="utf-8") as f:
    f.write(html_content)

print(f"✅ 선택창 포함 지도 생성 완료: {output_path}")
