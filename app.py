import streamlit as st
import geopandas as gpd
import folium
from folium.features import GeoJsonPopup, GeoJsonTooltip
from streamlit_folium import st_folium
import requests
import zipfile
import io
import os

st.title("Alaska Snowlines")

# ---------------- Download and extract ZIP: glacier outlines ----------------
ZENODO_URL = "https://zenodo.org/records/16944113/files/RGI2000-v7.0-G-01_alaska.gpkg.zip?download=1"


def load_glaciers(url):
    # Download ZIP into memory
    response = requests.get(url)
    response.raise_for_status()
    
    with zipfile.ZipFile(io.BytesIO(response.content)) as zf:
        gpkg_name = [f for f in zf.namelist() if f.endswith(".gpkg")][0]

        # Write the GPKG to a temp file
        with tempfile.NamedTemporaryFile(suffix=".gpkg", delete=False) as tmp:
            tmp.write(zf.read(gpkg_name))
            tmp_path = tmp.name

    gdf = gpd.read_file(tmp_path) # read with GeoPandas from the temp file
    os.remove(tmp_path) # remove tmp file
    return gdf

# Center map
gdf_proj = gdf.to_crs(epsg=3338)  # Alaska Albers
centroid = gdf_proj.geometry.centroid.unary_union.centroid
center = gpd.GeoSeries([centroid], crs=gdf_proj.crs).to_crs(epsg=4326)
center_coords = [center.y.iloc[0], center.x.iloc[0]]

# Create map
m = folium.Map(location=center_coords, zoom_start=4, tiles="CartoDB positron")

# ---------------- Add glacier polygons with popup ----------------
folium.GeoJson(
    gdf,
    name="Alaska Glaciers",
    style_function=lambda x: {
        "color": "blue",
        "weight": 0.5,
        "fillOpacity": 0.3,
    },
    popup=GeoJsonPopup(
        fields=["rgi_id", "glac_name", "cenlat", "cenlon", "area_km2", "zmin_m", "zmax_m"],
        aliases=["RGI ID:", "Name:", "Center Lat:", "Center Lon:", "Area (sq. km):", "Min elev (m):", "Max elev (m):"],
        localize=True,
        labels=True,
        style="background-color: white;",
    ),
    tooltip=GeoJsonTooltip(
        fields=["rgi_id", "glac_name"],
        aliases=["RGI ID:", "Name:"],
        sticky=True,
    ),
).add_to(m)

folium.LayerControl().add_to(m)

st_folium(m, width=800, height=600)

