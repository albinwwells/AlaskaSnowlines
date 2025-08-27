import streamlit as st
import pandas as pd
import numpy as np
import json
import datetime
import requests, zipfile, io, os
import matplotlib.pyplot as plt

st.set_page_config(
    page_title="Animation",
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
st.session_state["current_page"] = "animation"

# ---------------- Main page ----------------
gdf = st.session_state.get("gdf", None)
query_params = st.query_params
rgi_no_map = query_params.get("name", None)
rgi_no_man = None

# Allow manual input
manual_input = st.text_input("Enter a glacier name")

if manual_input is not None:
    if gdf is None:
        with st.spinner("Loading possible glaciers..."):
            ZENODO_URL = "https://zenodo.org/records/16959278/files/RGI2000-v7.0-G-01_alaska_2km2.csv?download=1"
            def load_glaciers(url):
                # Persistent cache folder
                cache_dir = "/tmp/alaska_glaciers"
                os.makedirs(cache_dir, exist_ok=True)
            
                csv_path = os.path.join(cache_dir, "RGI2000-v7.0-G-01_alaska.csv")
            
                # If already downloaded, read from cache
                if os.path.exists(csv_path):
                    gdf = gpd.read_file(csv_path)
                    return gdf
            
                # Download ZIP
                response = requests.get(url)
                response.raise_for_status()
                gdf = pd.read_csv(io.StringIO(response.text))
                return gdf
        
            # Load glaciers
            gdf = load_glaciers(ZENODO_URL)
            gdf = gdf[gdf["area_km2"] > 2].copy()
            gdf = gdf[~gdf["glac_name"].str.contains("_abl", case=False, na=False)].copy()

    # Case-insensitive substring match on rgi_id or glac_name
    matches = gdf[gdf["glac_name"].str.contains(manual_input, case=False, na=False)]

    if not matches.empty and len(matches) < 100:
        if len(matches) == 1:
            st.info(f"Found {len(matches)} possible match.")
        else:
            st.info(f"Found {len(matches)} possible matches. Please choose one:")
        selected = st.selectbox("Select glacier:", matches["glac_name"])
        rgi_no_man = selected.split(' Glacier')[0]
    else:
        if matches.empty:
            st.error("No matching glacier found.")


# ---------------- Show GIF instead of plotting ----------------
rgi_no = rgi_no_man if rgi_no_man is not None else rgi_no_map
if rgi_no is None:
    st.page_link("app.py", label="No glacier selected. Go back to the map selection or enter a glacier above.")
else:
    st.write(f"### Visualization for RGI v7: {rgi_no}")

    # Path to your GIF zip file
    gif_zip_fp = "https://zenodo.org/records/16961713/files/animations.zip?download=1"

    gif_pattern = os.path.join(gif_dir, f"{rgi_no}_*_animation.html")
    matching_gifs = glob.glob(gif_pattern)
    if matching_gifs:
        for gif_file in matching_gifs:
            st.write(f"Showing {os.path.basename(gif_file)}")
            with open(gif_file, "r") as f:
                html_content = f.read()
            st.components.v1.html(html_content, height=500)
    else:
        st.error(f"No animation available for {rgi_no} Glacier.")

