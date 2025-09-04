import streamlit as st
import geopandas as gpd
import pandas as pd
import requests, zipfile, io, os

st.set_page_config(
    page_title="Animation",
    layout="wide",         # optional: wide layout
    initial_sidebar_state="collapsed"  # <- hides/collapses sidebar
)

def nav():
    with st.sidebar:
        st.title("Navigation")
        st.page_link("https://alaskasnowlines.streamlit.app/", label="Home - glacier selection")
        st.page_link("https://alaskasnowlines.streamlit.app/plot_elev", label="Heatmap - elevation bins")
        st.page_link("https://alaskasnowlines.streamlit.app/plot_area", label="Heatmap - area bins")
        st.page_link("https://alaskasnowlines.streamlit.app/plot_gif", label="Glacier animations")
nav()

# hide_sidebar_style = """
#     <style>
#         [data-testid="stSidebar"] {display: none;}
#         [data-testid="stSidebarNav"] {display: none;}
#     </style>
# """
# st.markdown(hide_sidebar_style, unsafe_allow_html=True)
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
        with st.spinner("Loading glacier outlines..."):
            def load_glaciers(url):
                gdf = pd.read_csv(csv_path)
                return gdf
        
        # Load glaciers
        csv_path = os.path.join("data", "RGI2000-v7.0-G-01_alaska_2km2.csv")
        gdf = load_glaciers(csv_path)
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
        rgi_no_man = selected.replace(" Glacier", "").replace("_abl", "").strip()
        rgi_no_man = rgi_no_man.replace("/", "-")
    else:
        if matches.empty:
            st.error("No matching glacier found.")

@st.cache_data(show_spinner="Accessing data downloading options...", ttl=300)
def export_gif(url: str):
    response = requests.get(url)
    response.raise_for_status()
    return response.content
    
@st.cache_data(show_spinner="Downloading animation...", ttl=24*3600)
def download_gif_zip(url: str):
    response = requests.get(url)
    response.raise_for_status()
    return io.BytesIO(response.content)

@st.cache_data(show_spinner="Loading animation...", ttl=24*3600)
def get_animation_html(zip_bytes, rgi_no: str):
    with zipfile.ZipFile(zip_bytes) as zf:
        matching_files = [f for f in zf.namelist() if f.startswith(f"{rgi_no}") and f.endswith("_animation.html")]
        result = []
        for fname in matching_files:
            with zf.open(fname) as f:
                html_content = f.read().decode()
            pathrow = fname.split(f"{rgi_no}_")[1].split("_animation")[0]
            result.append((pathrow, html_content))
        return result
            
# ---------------- show animation ----------------
rgi_no = rgi_no_man if rgi_no_man is not None else rgi_no_map
if rgi_no is None:
    st.page_link("app.py", label="No glacier selected. Go back to the map selection or enter a glacier above.")
else:
    st.write(f"### Animation for {rgi_no} Glacier")

    if (ord(rgi_no[0]) >= 65) and (ord(rgi_no[0]) < 68): # from A thru C
        gif_zip_fp = f"https://zenodo.org/records/17054496/files/{rgi_no}.zip?download=1"
    elif (ord(rgi_no[0]) >= 68) and (ord(rgi_no[0]) < 74): # from D thru I
        gif_zip_fp = f"https://zenodo.org/records/17054526/files/{rgi_no}.zip?download=1"
    elif (ord(rgi_no[0]) >= 74) and (ord(rgi_no[0]) < 79): # from J thru N
        gif_zip_fp = f"https://zenodo.org/records/17054660/files/{rgi_no}.zip?download=1"
    elif (ord(rgi_no[0]) >= 79) and (ord(rgi_no[0]) < 84): # from O thru S
        gif_zip_fp = f"https://zenodo.org/records/17054835/files/{rgi_no}.zip?download=1"
    elif (ord(rgi_no[0]) >= 84) and (ord(rgi_no[0]) < 91): # from T thru Z
        gif_zip_fp = f"https://zenodo.org/records/17054907/files/{rgi_no}.zip?download=1"
    
    zip_bytes = download_gif_zip(gif_zip_fp)
    animations = get_animation_html(zip_bytes, rgi_no)
    
    if animations:
        for pathrow, html_content in animations:
            st.write(f"pathrow: {pathrow}")
            st.components.v1.html(html_content, height=800, scrolling=True)
            
        # download button
        st.download_button(
            label="Download animation",
            data=export_gif(gif_zip_fp),  # fetch bytes directly here
            file_name=f"{rgi_no}_animation.zip",
            mime="application/zip"
        )
    else:
        st.error(f"No animation available for {rgi_no} Glacier.")
