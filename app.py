import streamlit as st
import geopandas as gpd
import folium
from folium.features import GeoJsonTooltip
from streamlit_folium import st_folium
import requests
import zipfile
import os
import io
import tempfile

st.title("Alaska Snowlines")

# ---------------- Import shapefiles ----------------
ZENODO_URL = "https://zenodo.org/records/16944113/files/RGI2000-v7.0-G-01_alaska.gpkg.zip?download=1"

@st.cache_data(show_spinner="Loading glaciers from Zenodo...")
def load_glaciers(url):
    # Persistent cache folder
    cache_dir = "/tmp/alaska_glaciers"
    os.makedirs(cache_dir, exist_ok=True)

    gpkg_path = os.path.join(cache_dir, "RGI2000-v7.0-G-01_alaska.gpkg")

    # If already downloaded, read from cache
    if os.path.exists(gpkg_path):
        gdf = gpd.read_file(gpkg_path)
        return gdf

    # Download ZIP
    response = requests.get(url)
    response.raise_for_status()
    with zipfile.ZipFile(io.BytesIO(response.content)) as zf:
        gpkg_name = [f for f in zf.namelist() if f.endswith(".gpkg")][0]
        # Extract GPKG to cache
        zf.extract(gpkg_name, cache_dir)
        extracted_path = os.path.join(cache_dir, gpkg_name)
        # Rename to standard path
        os.rename(extracted_path, gpkg_path)

    gdf = gpd.read_file(gpkg_path)
    return gdf

# Load glaciers
gdf = load_glaciers(ZENODO_URL)
gdf = gdf[gdf["area_km2"] > 2].copy()

# ---------------- Lightweight map ----------------
with st.spinner("Simplifying geometries..."):
    outline_gdf = gdf[["geometry"]].copy()
    outline_gdf["geometry"] = outline_gdf.geometry.simplify(tolerance=0.01, preserve_topology=True) # simplify to help plotting

with st.spinner("Plotting glaciers..."):
    # ---------------- Map ----------------
    bounds = outline_gdf.total_bounds
    center = [(bounds[1] + bounds[3]) / 2, (bounds[0] + bounds[2]) / 2]

    m = folium.Map(location=center, zoom_start=4, tiles="CartoDB positron")

    # ---------------- Add outlines ----------------
    folium.GeoJson(
        outline_gdf,
        style_function=lambda x: {"color": "blue", "weight": 0.5, "fillOpacity": 0.1}
    ).add_to(m)

    # # ---------------- Add clickable centroids ----------------
    # for _, row in gdf.iterrows():
    #     lat, lon = row.get("cenlat"), row.get("cenlon")
    #     if lat is not None and lon is not None:
    #         popup = (
    #             f"RGI ID: {row['rgi_id']} | Name: {row['glac_name']}<br>"
    #             f"Lat: {lat} | Lon: {lon} | "
    #             f"Area: {row['area_km2']} sq.km | Min: {row['zmin_m']} m | Max: {row['zmax_m']} m"
    #         )
    #         folium.CircleMarker(
    #             location=[lat, lon],
    #             radius=3,
    #             color="red",
    #             fill=True,
    #             fill_color="red",
    #             popup=popup
    #         ).add_to(m)

    # ---------------- Layers & render ----------------
    folium.LayerControl().add_to(m)
    st_folium(m, width=800, height=600)

folium.LayerControl().add_to(m)

# Render map and capture clicks
map_data = st_folium(m, width=1000, height=600)

# # ---------------- Show popup_fields dynamically on click ----------------
# popup_fields = ["rgi_id", "glac_name", "cenlat", "cenlon", "area_km2", "zmin_m", "zmax_m"]
# existing_fields = [f for f in popup_fields if f in gdf.columns]

# if map_data and "last_active_drawing" in map_data and map_data["last_active_drawing"]:
#     feature = map_data["last_active_drawing"]
#     rgi_id = feature["properties"].get("rgi_id")
#     if rgi_id:
#         st.write("Selected glacier RGI ID:", rgi_id)
#         row = gdf[gdf["rgi_id"] == rgi_id]
#         st.write(row[existing_fields])

