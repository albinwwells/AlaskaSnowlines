import streamlit as st
import geopandas as gpd
import folium
from streamlit_folium import st_folium
import requests
import tempfile
import zipfile
import io
import os

st.title("Alaska Snowlines")

# Download and extract ZIP
ZENODO_URL = "https://zenodo.org/record/16943879/files/RGI2000-v7.0-G-01_02_alaska.gpkg.zip?download=1"

@st.cache_data(show_spinner="Loading glaciers from Zenodo...")
def load_glaciers(url):
    # Use a temporary directory for extraction
    with tempfile.TemporaryDirectory() as tmpdir:
        # Check if file already exists in cache dir
        cached_path = os.path.join(tmpdir, "RGI2000-v7.0-G-01_02_alaska.gpkg")
        if os.path.exists(cached_path):
            gdf = gpd.read_file(cached_path)
            return gdf

        # Download and extract
        response = requests.get(url)
        response.raise_for_status()
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

# Add glacier polygons
folium.GeoJson(
    gdf,
    name="Alaska Glaciers",
    style_function=lambda x: {
        "color": "blue",
        "weight": 0.5,
        "fillOpacity": 0.3,
    },
).add_to(m)

folium.LayerControl().add_to(m)

st_folium(m, width=800, height=600)

