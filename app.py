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
ZENODO_URL = "https://zenodo.org/records/16943975/files/RGI2000-v7.0-G-01_alaska.gpkg.zip?download=1"

@st.cache_data(show_spinner="Loading glaciers from Zenodo...")
def load_glaciers(url):
    # Download and extract
    response = requests.get(url)
    response.raise_for_status()
    with tempfile.TemporaryDirectory() as tmpdir:
        with zipfile.ZipFile(io.BytesIO(response.content)) as zf:
            zf.extractall(tmpdir)
            gpkg_path = [f for f in zf.namelist() if f.endswith(".gpkg")][0]
            gdf = gpd.read_file(os.path.join(tmpdir, gpkg_path))
    return gdf

# Load glaciers (cached)
gdf = load_glaciers(ZENODO_URL)

# Center map
center = [gdf.geometry.centroid.y.mean(), gdf.geometry.centroid.x.mean()]

# Create folium map
m = folium.Map(location=center, zoom_start=4, tiles="CartoDB positron")

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

