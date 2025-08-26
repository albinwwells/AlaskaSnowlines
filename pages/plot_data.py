import streamlit as st
import pandas as pd
import requests, zipfile, io
import matplotlib.pyplot as plt

st.set_page_config(layout="wide", page_title="Snowline Plot")

# ---------------- Fetch glacier snowline + melt CSVs ----------------
@st.cache_data(show_spinner="Fetching glacier data...")
def fetch_snowline_data(rgi_no: str):
    """Fetch snowline and melt extent CSVs from Zenodo for a given glacier number."""

    url = "https://zenodo.org/records/16947075/files/data.zip?download=1"
    response = requests.get(url)
    response.raise_for_status()

    with zipfile.ZipFile(io.BytesIO(response.content)) as zf:
        file_name = f"{rgi_no}.zip"
        if file_name not in zf.namelist():
            return None, None  # glacier not available

        with zf.open(file_name) as glacier_zip:
            with zipfile.ZipFile(glacier_zip) as gzf:
                glac_csvs = gzf.namelist()
                sl_csvs = [
                    f for f in glac_csvs 
                    if "snowline_elev_percentile" in f 
                    and "eos_corr" not in f 
                    and "eabin" not in f
                ]
                me_csvs = [f.replace("snowline", "melt_extent") for f in sl_csvs]
                return sl_csvs, me_csvs, gzf


# ---------------- Main page ----------------
query_params = st.query_params
rgi_id = query_params.get("rgi_id", None)

if rgi_id is None:
    st.warning("No glacier selected. Go back to the map and click a glacier.")
else:
    # Convert RGI ID → RGI number (your convention: 01.xxxxx)
    rgi_no = "01." + rgi_id[-5:]
    st.write(f"### Data for RGI v7 number {rgi_no}")

    sl_csvs, me_csvs, gzf = fetch_snowline_data(rgi_no)

    if sl_csvs is None:
        st.error("No snowline data found for this glacier.")
    else:
        for sl_csv in sl_csvs:
            with gzf.open(sl_csv) as f:
                df = pd.read_csv(f)

            st.subheader(f"Snowline file: {sl_csv}")
            st.dataframe(df.head())  # show preview

            # ---------------- Example plot ----------------
            fig, ax = plt.subplots(figsize=(8, 5))
            ax.plot(df["date"], df["elev"], marker="o", label="Snowline elevation")
            ax



