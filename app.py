import streamlit as st
import geopandas as gpd
import folium
from folium.features import GeoJsonTooltip
from streamlit_folium import st_folium
import requests
import zipfile
import io

st.title("Alaska Snowlines")

# ---------------- Download and read GPKG from Zenodo ----------------
ZENODO_URL = "https://zenodo.org/records/16944113/files/RGI2000-v7.0-G-01_alaska.gpkg.zip?download=1"

@st.cache_data(show_spinner="Loading glaciers...")
def load_glaciers(url):
    # Download ZIP
    response = requests.get(url)
    response.raise_for_status()
    with zipfile.ZipFile(io.BytesIO(response.content)) as zf:
        gpkg_name = [f for f in zf.namelist() if f.endswith(".gpkg")][0]
        gdf = gpd.read_file(f"/vsimem/{gpkg_name}", driver="GPKG")
        # Use pyogrio virtual file system to avoid writing temp files
        with zf.open(gpkg_name) as f:
            gdf = gpd.read_file(f)
    return gdf

gdf = load_glaciers(ZENODO_URL)

# ---------------- Lightweight map: only keep id + name + geometry ----------------
map_gdf = gdf[["rgi_id", "glac_name", "geometry"]].copy()

# ---------------- Center map ----------------
bounds = map_gdf.total_bounds  # [minx, miny, maxx, maxy]
center = [(bounds[1] + bounds[3]) / 2, (bounds[0] + bounds[2]) / 2]

# ---------------- Folium map ----------------
m = folium.Map(location=center, zoom_start=4, tiles="CartoDB positron")

# Add polygons with tooltip only (fast)
folium.GeoJson(
    map_gdf,
    style_function=lambda x: {"color": "blue", "weight": 0.5, "fillOpacity": 0.3},
    tooltip=GeoJsonTooltip(
        fields=["rgi_id", "glac_name"],
        aliases=["RGI ID:", "Name:"],
        sticky=True
    )
).add_to(m)

# Add layer control
folium.LayerControl().add_to(m)

# Render map once and capture clicks
map_data = st_folium(m, width=800, height=600)

# ---------------- Show popup_fields dynamically on click ----------------
popup_fields = ["rgi_id", "glac_name", "cenlat", "cenlon", "area_km2", "zmin_m", "zmax_m"]
existing_fields = [f for f in popup_fields if f in gdf.columns]

if map_data and "last_active_drawing" in map_data and map_data["last_active_drawing"]:
    feature = map_data["last_active_drawing"]
    rgi_id = feature["properties"].get("rgi_id")
    if rgi_id:
        st.write("Selected glacier RGI ID:", rgi_id)
        row = gdf[gdf["rgi_id"] == rgi_id]
        st.write(row[existing_fields])
