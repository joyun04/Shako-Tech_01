from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.templating import Jinja2Templates
import geopandas as gpd
import json
import os

app = FastAPI()
templates = Jinja2Templates(directory="templates")

# -----------------------------
# 파일 경로
# -----------------------------
buildings_path = r"D:/preprocessing/map/do_buld5.shp"
poi_path = r"D:/preprocessing/POI/yongdu_pois.shp"

# -----------------------------
# 데이터 불러오기
# ------------------------S-----
buildings = gpd.read_file(buildings_path, encoding='utf-8')
target_bdtp = ["02000", "02001", "02002", "02003"]
buildings = buildings[buildings["BDTYP_CD"].isin(target_bdtp)]
poi_gdf = gpd.read_file(poi_path, encoding='utf-8')

# 컬럼 문자열/공백 처리
buildings["BDTYP_CD"] = buildings["BDTYP_CD"].astype(str).str.strip()

# 좌표계 설정
if buildings.crs is None:
    buildings.set_crs(epsg=5179, inplace=True)
else:
    buildings = buildings.to_crs(epsg=5179)

if poi_gdf.crs is None:
    poi_gdf.set_crs(epsg=5179, inplace=True)
else:
    poi_gdf = poi_gdf.to_crs(epsg=5179)

# 유효한 geometry만 남기기
buildings = buildings[buildings.geometry.notnull()]
poi_gdf = poi_gdf[poi_gdf.geometry.notnull()]

# 건축물 필터
target_bdtp = ["02000", "02001", "02002", "02003"]
buildings = buildings[buildings["BDTYP_CD"].isin(target_bdtp)]

# -----------------------------
# 메인 페이지
# -----------------------------
@app.get("/", response_class=HTMLResponse)
def index(request: Request):
    categories = poi_gdf["category"].unique().tolist()
    return templates.TemplateResponse("index.html", {"request": request, "categories": categories})

# -----------------------------
# API: 특정 카테고리 버퍼 내 건축물 반환
# -----------------------------
@app.get("/api/buildings")
def get_buildings(category: str):
    subset = poi_gdf[poi_gdf["category"] == category]
    if subset.empty:
        return JSONResponse({"type": "FeatureCollection", "features": []})

    subset = subset.to_crs(epsg=5179)
    buildings_proj = buildings.to_crs(epsg=5179)

    buffer_union = subset.buffer(250)
    buffer_gdf = gpd.GeoDataFrame(geometry=buffer_union, crs=subset.crs)

    buildings_in_buffer = gpd.sjoin(buildings_proj, buffer_gdf, how="inner", predicate="intersects")

    if buildings_in_buffer.empty:
        return JSONResponse({"type": "FeatureCollection", "features": []})

    buildings_in_buffer = buildings_in_buffer.to_crs(epsg=4326)
    return JSONResponse(json.loads(buildings_in_buffer.to_json()))

# -----------------------------
# API: 전체 POI 반환
# -----------------------------
@app.get("/api/pois")
def get_pois():
    pois = poi_gdf.to_crs(epsg=4326)
    return JSONResponse(json.loads(pois.to_json()))
