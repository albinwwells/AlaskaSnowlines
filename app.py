import streamlit as st
import pandas as pd
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
ZENODO_URL = "https://zenodo.org/records/16947075/files/RGI2000-v7.0-G-01_alaska_2km2_reduc.gpkg.zip?download=1"

@st.cache_data(show_spinner="Loading glacier outlines...")
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
gdf = gdf[~gdf["glac_name"].str.contains("_abl", case=False, na=False)].copy()

# ---------------- Lightweight map ----------------
with st.spinner("Simplifying glacier geometries..."):
    outline_gdf = gdf[["geometry"]].copy()
    outline_gdf["geometry"] = outline_gdf.geometry.simplify(tolerance=0.001, preserve_topology=True) # simplify to help plotting

with st.spinner("Plotting glaciers..."):
    # ---------------- Map ----------------
    bounds = gdf.total_bounds
    # center = [(bounds[1] + bounds[3]) / 2, (bounds[0] + bounds[2]) / 2]
    center = [63.0, -148.0]

    m = folium.Map(location=center, zoom_start=5, tiles="CartoDB positron")

    # ---------------- Add outlines ----------------
    folium.GeoJson(
        outline_gdf,
        style_function=lambda x: {"color": "blue", "weight": 0.5, "fillOpacity": 0.1}
    ).add_to(m)

    # ---------------- Add clickable centroids ----------------
    for _, row in gdf.iterrows():
        lat, lon = row.get("cenlat"), row.get("cenlon")
        if lat is not None and lon is not None:
            popup_html = f"""
            <b>RGI ID:</b> {row['rgi_id']}<br>
            <b>Name:</b> {row['glac_name']}<br>
            <b>Area:</b> {round(row['area_km2'], 1)} km2<br>
            <b>Min elev:</b> {round(row['zmin_m'])} m<br>
            <b>Max elev:</b> {round(row['zmax_m'])} m<br>
            <button onclick="window.parent.postMessage({{'rgi_id': '{row['rgi_id']}'}}, '*')">
                Plot snowline data
            </button>
            """
            popup = folium.Popup(popup_html, max_width=500)
    
            folium.CircleMarker(
                location=[lat, lon],
                radius=1,
                color="blue",
                fill=True,
                fill_color="blue",
                popup=popup
            ).add_to(m)

    # ---------------- Layers & render ----------------
    folium.LayerControl().add_to(m)
    st_folium(m, width=1000, height=600)

folium.LayerControl().add_to(m)

# Render map and capture clicks
map_data = st_folium(m, width=1000, height=600)


selected_id = None
if map_data and "last_object_clicked_popup" in map_data:
    popup_html = map_data["last_object_clicked_popup"]
    if popup_html and "RGI ID:" in popup_html:
        selected_id = popup_html.split("RGI ID:")[1].split("<br>")[0].strip()

# ---------------- Fetch CSV when glacier selected ----------------
@st.cache_data(show_spinner="Fetching glacier data...")
def fetch_snowline_data(glac_csvs):
    sl_csvs = [f for f in glac_csvs if "snowline_elev_percentile" in f and "eos_corr" not in f and "eabin" not in f]
    me_csvs = [f.replace("snowline", "melt_extent") for f in sl_csvs]
    return sl_csvs, me_csvs
    
if selected_id:
    rgi_no = "01." + selected_id[-5:]
    st.write(f"### Data for RGI v7 number {rgi_no}")

    url = "https://zenodo.org/records/16947075/files/data.zip?download=1"
    response = requests.get(url)
    response.raise_for_status()
    with zipfile.ZipFile(io.BytesIO(response.content)) as zf:
        file_name = f"{rgi_no}.zip"
        if file_name in zf.namelist():
            with zf.open(file_name) as glacier_zip:
                with zipfile.ZipFile(glacier_zip) as gzf:            
                    glac_csvs = gzf.namelist()
                    sl_csvs, me_csvs = fetch_snowline_data(glac_csvs)

                    for sl_csv in sl_csvs:
                        with gzf.open(sl_csv) as f:
                            df = pd.read_csv(f)
                            st.dataframe(df)
                            # your plotting code goes here




