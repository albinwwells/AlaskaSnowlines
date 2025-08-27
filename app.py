import streamlit as st
import pandas as pd
import geopandas as gpd
import json
import folium
from folium.features import GeoJsonTooltip
from folium.plugins import MarkerCluster
from streamlit_folium import st_folium
import requests, zipfile, os, io
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

    csv_url = "https://zenodo.org/records/16961713/files/RGI2000-v7.0-G-01_alaska_2km2.csv?download=1"
    @st.cache_data(show_spinner="Loading possible glaciers...")
    def load_csv(url):
        # Persistent cache folder
        cache_dir = "/tmp/alaska_glaciers"
        os.makedirs(cache_dir, exist_ok=True)
    
        csv_path = os.path.join(cache_dir, "RGI2000-v7.0-G-01_alaska.csv")
    
        # If already downloaded, read from cache
        if os.path.exists(csv_path):
            df = gpd.read_file(csv_path)
            return df
    
        # Download ZIP
        response = requests.get(url)
        response.raise_for_status()
        df = pd.read_csv(io.StringIO(response.text))
        return df
    
    # Load glaciers
    df = load_csv(csv_url)
    df = df[df["area_km2"] > 2].copy()
    df = df[~df["glac_name"].str.contains("_abl", case=False, na=False)].copy()
    st.session_state["gdf"] = df
    
    # ---------------- Lightweight map ----------------
    # with st.spinner("Simplifying glacier geometries..."):
    #     outline_gdf = gdf[["geometry"]].copy()
    #     outline_gdf["geometry"] = outline_gdf.geometry.simplify(tolerance=0.001, preserve_topology=True) # simplify to help plotting
    
    # ---------------- Map ----------------
    center = [61.0, -146.0]

    m = folium.Map(location=center, zoom_start=4, tiles="CartoDB positron", name="Basemap")
    folium.TileLayer(
        tiles="https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}",
        attr="Esri",
        name="Esri Satellite",
        overlay=False,
        control=True
    ).add_to(m)
    
    @st.cache_resource
    def get_outline_geojson(_gdf):
        return gdf.to_json()
    
    with st.spinner("Adding outlines..."):
        geojson_data = get_outline_geojson(gdf)
        folium.GeoJson(
            json.loads(geojson_data),
            style_function=lambda x: {"color": "blue", "weight": 0.75, "fillOpacity": 0}
        ).add_to(m)
    
    # with st.spinner("Adding outlines..."):
    #     # ---------------- Add outlines ----------------
    #     folium.GeoJson(
    #         gdf, # outline_gdf
    #         style_function=lambda x: {"color": "blue", "weight": 0.75, "fillOpacity": 0}
    #     ).add_to(m)  
        
    with st.spinner("Plotting glaciers..."):
        cluster = MarkerCluster().add_to(m)
        
        # ---------------- Add clickable centroids ----------------
        for _, row in df.iterrows():
            lat, lon = row.get("cenlat"), row.get("cenlon")
            if lat is not None and lon is not None:
                rgi_no = "01." + row['rgi_id'][-5:]
                # glac_gdf = gdf[gdf['rgi_id'] == row['rgi_id']]
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
                if row['area_km2'] < 50:
                    folium.CircleMarker(
                        location=[lat, lon],
                        radius=2,
                        color="blue",
                        fill=True,
                        fill_color="blue",
                        popup=popup
                    ).add_to(cluster)
                else:
                    # Large glaciers added directly to the map
                    folium.CircleMarker(
                        location=[lat, lon],
                        radius=2,
                        color="blue",
                        fill=True,
                        fill_color="blue",
                        popup=popup
                    ).add_to(m)
            
                # folium.CircleMarker(
                #     location=[lat, lon],
                #     radius=2,
                #     color="blue",
                #     fill=True,
                #     fill_color="blue",
                #     popup=popup
                # ).add_to(cluster)
    
        # ---------------- Layers & render ----------------
        folium.LayerControl().add_to(m)
        st_folium(m, width=800, height=600)
    
    folium.LayerControl().add_to(m)

    # Render map and capture clicks
    map_data = st_folium(m, width=800, height=600)
