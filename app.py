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

gdf = load_glaciers(ZENODO_URL)
center = [gdf.geometry.centroid.y.mean(), gdf.geometry.centroid.x.mean()] # Center map
m = folium.Map(location=center, zoom_start=4, tiles="CartoDB positron") # Create folium map

# ---------------- Add glacier polygons ----------------
folium.GeoJson(
    gdf,
    style_function=lambda x: {"color": "blue", "weight": 0.5, "fillOpacity": 0.3},
    tooltip=folium.GeoJsonTooltip(
        fields=["rgi_id", "glac_name"], 
        aliases=["RGI ID:", "Name:"],
        sticky=True
    )
).add_to(m)

# Render map in Streamlit
map_data = st_folium(m, width=800, height=600)

# ---------------- Add pop-ups on click ----------------
popup_fields = ["rgi_id", "glac_name", "cenlat", "cenlon", "area_km2", "zmin_m", "zmax_m"]
existing_fields = [f for f in popup_fields if f in gdf.columns]

# Check if user clicked a feature
if map_data and "last_active_drawing" in map_data and map_data["last_active_drawing"]:
    feature = map_data["last_active_drawing"]
    rgi_id = feature["properties"]["rgi_id"]
    st.write("Selected glacier RGI ID:", rgi_id)

    # Show additional info only for this feature
    row = gdf[gdf["rgi_id"] == rgi_id]
    st.write(row[existing_fields])
    
# ---------------- Add layers ----------------
folium.LayerControl().add_to(m)
st_folium(m, width=800, height=600)

