import requests
import folium
from folium.plugins import MarkerCluster
import geopandas as gpd
from shapely.geometry import Point
from concurrent.futures import ThreadPoolExecutor
import time

#특정 poi를 긁어오기위해 kakao map을 활용했습니다
# https://apis.map.kakao.com/
# https://apis.map.kakao.com/web/documentation/#CategoryCode
# * 트래킹 제한: 1일 300,000회 사용가능합니다


import requests
import folium
import collections
from tinydb import TinyDB,Query
import pandas as pd

# # 잘작동 되는지 확인용 (Test)
# # kakao api 사용하기 위한 key
app_key = 'KakaoAK' + 'f7dea420445453a99101987bcf736ac3'
url = 'https://dapi.kakao.com/v2/local/search/category.json'
# params = {
#     'category_group_code' : 'FD6',
#     'page': 1,
#     'rect': '127.0085280000,37.5357715389,127.1221115536,37.4573204481',
# }
# headers  = {
#     'Authorization': 'KakaoAK f7dea420445453a99101987bcf736ac3'
# }
# resp = requests.get(url, params=params, headers=headers)
# # 바이트 → 문자열 → JSON
# # resp.json()을 쓰면 내부적으로 utf-8로 디코딩해서 dict로 반환
# data = resp.json()
# # 카카오 로컬 API 기준: 'documents' key에 장소 정보 리스트
# documents = data['documents']
# # 확인~~
# df = pd.DataFrame(documents)
# print(df.head())

print("##########***************##################")
import requests
import folium
from folium.plugins import MarkerCluster
from concurrent.futures import ThreadPoolExecutor
import geopandas as gpd

app_key = 'KakaoAK f7dea420445453a99101987bcf736ac3'

# 카카오 POI 재
# =====================
def get_poi_list(start_x, start_y, end_x, end_y, category='HP8', max_count=45):
    offset = 0.000005
    page = 1
    results = []

    url = 'https://dapi.kakao.com/v2/local/search/category.json'
    headers = {'Authorization': app_key}

    while True:
        params = {
            'category_group_code': category,
            'rect': f'{start_x-offset},{start_y-offset},{end_x+offset},{end_y+offset}',
            'page': page
        }

        try:
            resp = requests.get(url, params=params, headers=headers)
            resp.raise_for_status()
        except Exception as e:
            print(f"API 호출 실패({category}):", e)
            return results

        data = resp.json()
        total_count = data['meta']['total_count']

        if total_count > max_count:
            mid_x = (start_x + end_x) / 2
            mid_y = (start_y + end_y) / 2
            results.extend(get_poi_list(start_x, start_y, mid_x, mid_y, category, max_count))
            results.extend(get_poi_list(mid_x, start_y, end_x, mid_y, category, max_count))
            results.extend(get_poi_list(start_x, mid_y, mid_x, end_y, category, max_count))
            results.extend(get_poi_list(mid_x, mid_y, end_x, end_y, category, max_count))
            return results
        else:
            results.extend(data['documents'])
            if data['meta']['is_end']:
                return results
            else:
                page += 1
                time.sleep(0.2)  # 속도 제한 회피

# 지도 생성 + SHP 저장
# =====================
def draw_map_with_pois(poi_dict, center=None, zoom_start=15, shp_path=None):
    colors = {'SC4':'blue','PS3':'green','SW8':'orange','HP8':'red'}
    names = {'SC4':'학교','PS3':'어린이집','SW8':'지하철역','HP8':'병원'}

    # 전체 POI 리스트
    all_pois = [poi for plist in poi_dict.values() for poi in plist]
    if not all_pois:
        print("데이터 없음")
        return None

    if center is None:
        lats = [float(h['y']) for h in all_pois]
        lngs = [float(h['x']) for h in all_pois]
        center = (sum(lats)/len(lats), sum(lngs)/len(lngs))

    # 지도 생성
    m = folium.Map(location=center, zoom_start=zoom_start)
    marker_cluster = MarkerCluster().add_to(m)

    for cat, poi_list in poi_dict.items():
        for h in poi_list:
            lat, lng = float(h['y']), float(h['x'])
            name = h.get('place_name', names[cat])
            tel = h.get('phone', '정보없음')
            popup_text = f"<b>{name}</b><br>전화: {tel}<br>범주: {names[cat]}"
            folium.Marker(
                location=(lat, lng),
                popup=popup_text,
                icon=folium.Icon(color=colors[cat], icon='info-sign')
            ).add_to(marker_cluster)

    # 범례
    legend_html = '''
    <div style="
    position: fixed; 
    top: 50px; left: 10px; width: 130px; height: 120px; 
    border:2px solid grey; z-index:9999; font-size:14px;
    background-color:white; padding:10px;">
    <b>범례</b><br>
    <i style="color:blue">■</i> 학교<br>
    <i style="color:green">■</i> 어린이집<br>
    <i style="color:orange">■</i> 지하철역<br>
    <i style="color:red">■</i> 병원
    </div>
    '''
    m.get_root().html.add_child(folium.Element(legend_html))

    # SHP 저장
    if shp_path:
        shp_data = []
        for cat, poi_list in poi_dict.items():
            for h in poi_list:
                shp_data.append({
                    'place_name': h.get('place_name'),
                    'category': names[cat],
                    'phone': h.get('phone', ''),
                    'geometry': Point(float(h['x']), float(h['y']))
                })
        gdf = gpd.GeoDataFrame(shp_data, geometry='geometry')
        gdf.set_crs(epsg=4326, inplace=True)
        gdf.to_file(shp_path, encoding='utf-8')
        print(f"SHP 저장 완료: {shp_path}")

    return m

# 실행쓰~~~~~
# =====================
if __name__ == "__main__":
    start_lng, end_lng = 127.036, 127.046
    start_lat, end_lat = 37.577, 37.587
    jump_x = jump_y = 0.005

    categories = ['SC4','PS3','SW8','HP8']
    poi_dict = {cat: [] for cat in categories}

    # 범위 내 POI 수집
    def fetch_category(cat):
        x = start_lng
        cat_results = []
        while x < end_lng:
            next_x = min(x + jump_x, end_lng)
            y = start_lat
            while y < end_lat:
                next_y = min(y + jump_y, end_lat)
                cat_results.extend(get_poi_list(x, y, next_x, next_y, category=cat))
                y = next_y
            x = next_x
        return cat_results

    with ThreadPoolExecutor(max_workers=4) as executor:
        futures = {executor.submit(fetch_category, cat): cat for cat in categories}
        for f in futures:
            cat = futures[f]
            poi_dict[cat].extend(f.result())

    # 지도 생성 + SHP 저장
    map_yongdu = draw_map_with_pois(poi_dict, shp_path="yongdu_pois.shp")
    if map_yongdu:
        map_yongdu.save("yongdu_pois_map.html")
        print("지도 파일 생성 완료: yongdu_pois_map.html")