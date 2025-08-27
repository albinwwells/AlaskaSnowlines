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

# st.title("Alaska Snowlines")
st.set_page_config(
    page_title="Alaska Snowlines",
    layout="wide",         # optional: wide layout
    initial_sidebar_state="collapsed"  # <- hides/collapses sidebar
)

hide_sidebar_style = """
    <style>
        [data-testid="stSidebar"] {display: none;}
        [data-testid="stSidebarNav"] {display: none;}
    </style>
"""
st.markdown(hide_sidebar_style, unsafe_allow_html=True)

st.session_state["current_page"] = "map"
if st.session_state.get("current_page") == "map":    
    # ---------------- Import shapefiles ----------------
    ZENODO_URL = "https://zenodo.org/records/16961713/files/RGI2000-v7.0-G-01_alaska_2km2_reduc.gpkg.zip?download=1"
    
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
    # st.session_state["gdf"] = gdf
    
    # ---------------- Lightweight map ----------------
    # with st.spinner("Simplifying glacier geometries..."):
    #     outline_gdf = gdf[["geometry"]].copy()
    #     outline_gdf["geometry"] = outline_gdf.geometry.simplify(tolerance=0.001, preserve_topology=True) # simplify to help plotting
    
    with st.spinner("Plotting glaciers..."):
        # ---------------- Map ----------------
        bounds = gdf.total_bounds
        # center = [(bounds[1] + bounds[3]) / 2, (bounds[0] + bounds[2]) / 2]
        center = [61.0, -146.0]
    
        m = folium.Map(location=center, zoom_start=4, tiles="CartoDB positron")
    
        # ---------------- Add outlines ----------------
        folium.GeoJson(
            gdf, # outline_gdf
            style_function=lambda x: {"color": "blue", "weight": 0.5, "fillOpacity": 0.1}
        ).add_to(m)
    
        # ---------------- Add clickable centroids ----------------
        for _, row in gdf.iterrows():
            lat, lon = row.get("cenlat"), row.get("cenlon")
            if lat is not None and lon is not None:
                rgi_no = "01." + row['rgi_id'][-5:]
                glac_gdf = gdf[gdf['rgi_id'] == row['rgi_id']]
                plot_url1 = f"https://alaskasnowlines.streamlit.app/plot_elev?rgi_no={rgi_no}"
                plot_url2 = f"https://alaskasnowlines.streamlit.app/plot_area?rgi_no={rgi_no}"
                try:
                    glac_name_short = row['glac_name'].split(' Glacier')[0]
                    plot_url3 = f"https://alaskasnowlines.streamlit.app/plot_gif?name={glac_name_short}"
                except:
                    plot_url3 = f"https://alaskasnowlines.streamlit.app/plot_gif"
                
                popup_html = f"""
                <b>RGI ID:</b> {row['rgi_id']}<br>
                <b>Name:</b> {row['glac_name']}<br>
                <b>Area:</b> {round(row['area_km2'], 1)} km2<br>
                <b>Min elev:</b> {round(row['zmin_m'])} m<br>
                <b>Max elev:</b> {round(row['zmax_m'])} m<br>
                <a href="{plot_url1}" target="_blank" style="
                    display:inline-block;
                    margin-top:5px;
                    padding:4px 8px;
                    background:#007BFF;
                    color:white;
                    text-decoration:none;
                    border-radius:4px;">
                    Plot data (elevation bins)
                </a>
                <br>
                <a href="{plot_url2}" target="_blank" style="
                    display:inline-block;
                    margin-top:5px;
                    padding:4px 8px;
                    background:#007BFF;
                    color:white;
                    text-decoration:none;
                    border-radius:4px;">
                    Plot data (area bins)
                </a>
                <br>
                <a href="{plot_url3}" target="_blank" style="
                    display:inline-block;
                    margin-top:5px;
                    padding:4px 8px;
                    background:#007BFF;
                    color:white;
                    text-decoration:none;
                    border-radius:4px;">
                    Animate data
                </a>
                """
                popup = folium.Popup(popup_html, max_width=500)
        
                # folium.GeoJson(
                #     glac_gdf,
                #     style_function=lambda x: {"color": "blue", "weight": 0.5, "fillOpacity": 0.1},
                #     popup=popup
                # ).add_to(m)
                folium.CircleMarker(
                    location=[lat, lon],
                    radius=2,
                    color="blue",
                    fill=True,
                    fill_color="blue",
                    popup=popup
                ).add_to(m)
    
        # ---------------- Layers & render ----------------
        folium.LayerControl().add_to(m)
        # st_folium(m, width=800, height=600)
    
    folium.LayerControl().add_to(m)

    # Render map and capture clicks
    map_data = st_folium(m, width=800, height=600)
