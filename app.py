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

## URL to zipped Alaska shapefile (RGI v7.0)
#URL = "https://daacdata.apps.nsidc.org/pub/DATASETS/nsidc0770_rgi_v7/RGI2000-v7.0-regions.zip"

#@st.cache_data(show_spinner="Downloading RGI Alaska shapefile...")
#def load_glacier_data(url):
#    # Download the ZIP
#    response = requests.get(url)
#    response.raise_for_status()

#    with tempfile.TemporaryDirectory() as tmpdir:
#        with zipfile.ZipFile(io.BytesIO(response.content)) as zf:
#            zf.extractall(tmpdir)
#            # Find .shp inside extracted files
#            shp_path = [f for f in zf.namelist() if f.endswith(".shp")][0]
#            full_path = os.path.join(tmpdir, shp_path)
#            gdf = gpd.read_file(full_path)
#    return gdf

## Load cached data
#gdf = load_glacier_data(URL)

# Local path to shapefile
RGI_shapefile_path = "data/RGI2000-v7.0-G-01_alaska.shp"

# Load shapefile
gdf = gpd.read_file(RGI_shapefile_path)

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

