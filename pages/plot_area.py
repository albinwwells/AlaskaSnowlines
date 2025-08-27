import streamlit as st
import pandas as pd
import numpy as np
import json
import datetime
import requests, zipfile, io, os
import matplotlib.pyplot as plt

st.set_page_config(
    page_title="Plot (equal area bins)",
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
st.session_state["current_page"] = "plot_area"

# ---------------- plotting functions ----------------
def plot_db_heatmap(db_bin, dates, bins_center, binned_area, set_ymin, set_ymax, glacno, cmap='RdYlBu', cbar_label='Backscatter [dB]', 
                    ylabel=r'Cumulative area [$km^2$]', glac_name_dict={}, figsize=(9,6), bins2plot_lowerquantile=2, 
                    bins2plot_upperquantile=98, frame_cut=0, title_info='', **kwargs):
    """" Heatmap plotting function """
    fig, ax = plt.subplots(figsize=figsize)
    
    dates_12d = pd.date_range(dates[frame_cut], dates[-1], freq='12D')
    dates_12d_str = [x.strftime('%Y%m%d') for x in dates_12d]
    db_bin_12d = np.zeros((db_bin.shape[0], len(dates_12d)))
    db_bin_12d[:] = np.nan
    dates_str = []
    for ndate, date in enumerate(dates_12d_str):
        date_np = np.datetime64(f'{date[:4]}-{date[4:6]}-{date[6:]}').astype('datetime64[ns]')
        if date_np in dates:
            date_idx = np.where(dates == date_np)[0][0]
            db_bin_12d[:,ndate] = db_bin[:,date_idx]
            dates_str.append(date)

    dbmin = np.nanpercentile(db_bin, 2)
    dbmax = np.nanpercentile(db_bin, 98)

    bin_sizes = np.diff(bins_center)
    bin_halfsize = bin_sizes[0]/2
    if ylabel == 'Elevation [m a.s.l.]':
        assert np.all(bin_sizes == bin_sizes[0]) == True, 'Elevation bins are not regularly spaced.'

    cax = ax.imshow(db_bin_12d, cmap=cmap, vmin=dbmin, vmax=dbmax, interpolation='nearest', aspect='auto', 
                    origin='lower', extent=[dates_12d[0], dates_12d[-1], set_ymin, set_ymax])

    # plot additional data from **kwargs
    line_plot = kwargs.get('line_plot', [])
    if line_plot:
        for data in line_plot:
            x, y, c, ls, lw, label = data
            ax.plot(x, y, c=c, ls=ls, lw=lw, label=label)
        ax.legend(loc='lower right')

    # label by glacier number or name, if available
    if glacno in glac_name_dict.keys():
        glac_name = glac_name_dict[glacno]
    else:
        glac_name = str(glacno)
    ax.set_title(glac_name+title_info)
    ax.set_ylabel(ylabel)
    ax.set_xlim([dates_12d[0], dates_12d[-1]])
    ax.set_ylim([set_ymin, set_ymax])
    cbar = fig.colorbar(cax, orientation='vertical', label=cbar_label)

    return fig

# ---------------- Fetch glacier snowline + melt CSVs ----------------
@st.cache_data(show_spinner="Fetching glacier data...")
def fetch_snowline_data(rgi_no: str):
    """Fetch snowline and melt extent CSVs for a given glacier number."""
    json_url = "https://zenodo.org/records/16961713/files/rgi_data_links.json?download=1"
    response = requests.get(json_url)
    response.raise_for_status()
    rgi_index = response.json()  # dictionary: rgi_no to zip URL
    
    rgi_key = (rgi_no + ".zip").strip()
    zip_name = rgi_index[rgi_key]
    zip_url = f"https://zenodo.org/records/16961713/files/{zip_name}?download=1"
    
    # Download the outer zip
    response = requests.get(zip_url)
    response.raise_for_status()

    sl_list, me_list, db_list, hyps_list, pr_list = [], [], [], [], []

    with zipfile.ZipFile(io.BytesIO(response.content)) as zf:
        file_name = f"{rgi_no}.zip"
        if file_name not in zf.namelist():
            return None, None, None, None, None

        # Extract inner ZIP as bytes
        with zf.open(file_name) as inner_zip_file:
            with zipfile.ZipFile(inner_zip_file) as gzf:
                for fname in gzf.namelist():
                    if "snowline_elev_percentile" in fname and "eos_corr" not in fname and "eabin" in fname:
                        sl_list.append(gzf.read(fname).decode())
                        me_list.append(gzf.read(fname.replace("snowline", "melt_extent")).decode())
                        db_list.append(gzf.read(fname.replace("snowline_elev_percentile", "db_bin_mean")).decode())
                        hyps_list.append(gzf.read(fname.replace("snowline_elev_percentile", "hypsometry")).decode())
                        pr_list.append(fname.split("_snowline_elev_percentile_")[-1][:-10])

    return sl_list, me_list, db_list, hyps_list, pr_list

# ---------------- Main page ----------------
gdf = st.session_state.get("gdf", None)
query_params = st.query_params
rgi_no_map = query_params.get("rgi_no", None)
rgi_no_man = None

# Allow manual input
manual_input = st.text_input("Enter a glacier name or RGI number:")

if manual_input is not None:
    if gdf is None:
        with st.spinner("Loading possible glaciers..."):
            ZENODO_URL = "https://zenodo.org/records/16961713/files/RGI2000-v7.0-G-01_alaska_2km2.csv?download=1"
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
    matches = gdf[
        gdf["rgi_id"].str.contains(manual_input, case=False, na=False) |
        gdf["glac_name"].str.contains(manual_input, case=False, na=False)
    ]

    if not matches.empty and len(matches) < 100:
        if len(matches) == 1:
            st.info(f"Found {len(matches)} possible match.")
        else:
            st.info(f"Found {len(matches)} possible matches. Please choose one:")
        selected = st.selectbox(
            "Select glacier:",
            matches["rgi_id"],
            format_func=lambda rid: f"{rid} – {matches.loc[matches['rgi_id']==rid, 'glac_name'].values[0]}"
        )
        rgi_no_man = "01." + selected[-5:]
    else:
        if matches.empty:
            st.error("No matching glacier found.")

# ---------------- filter date range ----------------
def dates_filter_for_plotting(df, date_start='2017-01-01', date_end='2025-01-01'):
    df.columns = pd.to_datetime(df.columns)
    df_filt = df.loc[:, (df.columns >= date_start) & (df.columns < date_end)]
    return df_filt

default_start = datetime.date(2017, 1, 1)
default_end = datetime.date(2025, 1, 1)
date_range = st.slider("Select plot date range:", min_value=datetime.date(2016, 1, 1), max_value=datetime.date(2025, 1, 1),
                       value=(default_start, default_end), format="YYYY-MM-DD")
date_start, date_end = date_range[0].strftime("%Y-%m-%d"), date_range[1].strftime("%Y-%m-%d")


# plot data
rgi_no = rgi_no_man if rgi_no_man is not None else rgi_no_map
if rgi_no is None:
    # st.warning("No glacier selected. Go back to the map and click a glacier.")
    st.page_link("app.py", label="No glacier selected. Go back to the map selection or enter a glacier above.")
else:
    # Convert RGI ID → RGI number (your convention: 01.xxxxx)
    st.write(f"### Data for RGI v7: {rgi_no}")
    sl_dfs, me_dfs, db_dfs, hyps_dfs, prs = fetch_snowline_data(rgi_no)

    if sl_dfs is None:
        st.error("No snowline data found for this glacier.")
    else:
        for sl_df, me_df, db_df, hyps_df, pr in zip(sl_dfs, me_dfs, db_dfs, hyps_dfs, prs):
            with st.spinner("Generating plots..."):
                sl_df = pd.read_csv(io.StringIO(sl_df), index_col=0)
                sl_df.index = pd.to_datetime(sl_df.index, format='%Y-%m-%d')
                me_df = pd.read_csv(io.StringIO(me_df), index_col=0)
                me_df.index = pd.to_datetime(me_df.index, format='%Y-%m-%d')
                db_df = pd.read_csv(io.StringIO(db_df), index_col=0)
                db_df = dates_filter_for_plotting(db_df, date_start=date_start, date_end=date_end)
                hyps_df = pd.read_csv(io.StringIO(hyps_df), index_col=0)
                
                glac_zbins_center = np.array(hyps_df.index.tolist())
                glac_bin_sizes = np.diff(glac_zbins_center)
                glac_bin_halfsize = glac_bin_sizes[0]/2
                binned_area = np.array(hyps_df.iloc[:, 0].tolist())
                set_ymin, set_ymax = 0, np.sum(binned_area)/1e6
    
                dates = np.array(db_df.columns.tolist()).astype('datetime64[ns]')
                glac_binned_data = np.array(db_df.to_numpy())
            
                dates_per = np.array(me_df.index.tolist()).astype('datetime64[ns]')
                me_elev_per = np.array(me_df.iloc[:, 0].tolist())/1e6
                dates_sl_per = np.array(sl_df.index.tolist()).astype('datetime64[ns]')
                sl_elev_per = np.array(sl_df.iloc[:, 0].tolist())/1e6
    
                # ---------------- Plot ----------------
                fig = plot_db_heatmap(db_bin=glac_binned_data,  dates=dates, bins_center=glac_zbins_center,
                                      binned_area=binned_area, set_ymin=set_ymin, set_ymax=set_ymax,
                                      glacno=rgi_no, title_info=f" (pathrow: {pr})", figsize=(12, 4), 
                                      line_plot=[(dates_per, me_elev_per, 'k', '-', 0.7, 'Melt extent'),
                                                 (dates_per, sl_elev_per, 'k', '-.', 0.7, 'Snowline')])
                st.pyplot(fig)
