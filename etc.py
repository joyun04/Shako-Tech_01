import geopandas as gpd

gdf = gpd.read_file("D:/preprocessing/map/do_buld5.shp", encoding="utf-8")
buildings.to_file("do_buld5.geojson", driver="GeoJSON", encoding="utf-8")
gdf = gpd.read_file("D:/preprocessing/POI/yongdu_pois.shp", encoding="utf-8")
gdf.to_file("yongdu_pois.geojson", driver="GeoJSON", encoding="utf-8")
