import streamlit as st
import pandas as pd
import numpy as np
import json
import requests, zipfile, io
import matplotlib.pyplot as plt

st.set_page_config(
    page_title="Alaska Snowlines",
    layout="wide",         # optional: wide layout
    initial_sidebar_state="collapsed"  # <- hides/collapses sidebar
)
st.session_state["current_page"] = "plot"

# ---------------- plotting functions ----------------
# def plot_db_heatmap(db_bin, dates, bins_center, binned_area, set_ymin, set_ymax, glacno,
#                     cmap='RdYlBu', cbar_label='db', ylabel='Elevation [m a.s.l.]', glac_name_dict={}, figsize=(9,6),
#                     bins2plot_lowerquantile=2, bins2plot_upperquantile=98, frame_cut=0, title_info='', **kwargs):
#     """Heatmap plotting function for Streamlit."""
    
#     fig, ax = plt.subplots(figsize=figsize)
    
#     # interpolate to 12-day intervals
#     dates_12d = pd.date_range(dates[frame_cut], dates[-1], freq='12D')
#     db_bin_12d = np.full((db_bin.shape[0], len(dates_12d)), np.nan)
    
#     for ndate, date in enumerate(dates_12d):
#         if date in dates:
#             idx = np.where(dates == date)[0][0]
#             db_bin_12d[:, ndate] = db_bin[:, idx]

#     # set color scale
#     dbmin = np.nanpercentile(db_bin, bins2plot_lowerquantile)
#     dbmax = np.nanpercentile(db_bin, bins2plot_upperquantile)

#     bin_sizes = np.diff(bins_center)
#     bin_halfsize = bin_sizes[0]/2
#     if ylabel == 'Elevation [m a.s.l.]':
#         assert np.all(bin_sizes == bin_sizes[0]), "Elevation bins not regularly spaced."

#     # plot heatmap
#     cax = ax.imshow(
#         db_bin_12d, cmap=cmap, vmin=dbmin, vmax=dbmax,
#         interpolation='nearest', aspect='auto', origin='lower',
#         extent=[dates_12d[0], dates_12d[-1], set_ymin, set_ymax]
#     )

#     # optional additional line plots
#     for data in kwargs.get('line_plot', []):
#         x, y, c, ls, lw, label = data
#         ax.plot(x, y, c=c, ls=ls, lw=lw, label=label)
#     if kwargs.get('line_plot'):
#         ax.legend(loc='lower right')

#     # title
#     glac_name = glac_name_dict.get(glacno, str(glacno))
#     ax.set_title(glac_name + title_info)
#     ax.set_ylabel(ylabel)
#     ax.set_xlim([dates_12d[0], dates_12d[-1]])
#     ax.set_ylim([set_ymin, set_ymax])

#     # colorbar
#     fig.colorbar(cax, orientation='vertical', label=cbar_label)

#     # display
#     st.pyplot(fig)
def plot_db_heatmap(db_bin, dates, bins_center, binned_area, set_ymin, set_ymax, glacno, cmap='RdYlBu', cbar_label='db', 
                    ylabel='Elevation [m a.s.l.]', glac_name_dict={}, figsize=(9,6), bins2plot_lowerquantile=2, 
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

st.set_page_config(layout="wide", page_title="Snowline Plot")

# ---------------- Fetch glacier snowline + melt CSVs ----------------
@st.cache_data(show_spinner="Fetching glacier data...")
def fetch_snowline_data(rgi_no: str):
    """Fetch snowline and melt extent CSVs for a given glacier number."""
    json_url = "https://zenodo.org/records/16956246/files/rgi_data_links.json?download=1"
    response = requests.get(json_url)
    response.raise_for_status()
    rgi_index = response.json()  # dictionary: rgi_no to zip URL
    
    rgi_key = (rgi_no + ".zip").strip()
    zip_name = rgi_index[rgi_key]
    zip_url = f"https://zenodo.org/records/16956246/files/{zip_name}?download=1"
    
    # Download the outer zip
    response = requests.get(zip_url)
    response.raise_for_status()

    sl_list, me_list, db_list, hyps_list = [], [], [], []

    with zipfile.ZipFile(io.BytesIO(response.content)) as zf:
        file_name = f"{rgi_no}.zip"
        if file_name not in zf.namelist():
            return None, None, None, None

        # Extract inner ZIP as bytes
        with zf.open(file_name) as inner_zip_file:
            with zipfile.ZipFile(inner_zip_file) as gzf:
                for fname in gzf.namelist():
                    if "snowline_elev_percentile" in fname and "eos_corr" not in fname and "eabin" not in fname:
                        sl_list.append(gzf.read(fname).decode())
                        me_list.append(gzf.read(fname.replace("snowline", "melt_extent")).decode())
                        db_list.append(gzf.read(fname.replace("snowline_elev_percentile", "db_bin_mean")).decode())
                        hyps_list.append(gzf.read(fname.replace("snowline_elev_percentile", "hypsometry")).decode())
                        st.write('sl_list:',sl_list)
                        st.write('fname:',fname)

                        sl_dfs = [pd.read_csv(zf.open(sl_csv), index_col=0) for sl_csv in sl_list]
                        me_dfs = [pd.read_csv(zf.open(me_csv), index_col=0) for me_csv in me_list]
                        db_dfs = [pd.read_csv(zf.open(db_csv), index_col=0) for db_csv in dp_list]
                        hyps_dfs = [pd.read_csv(zf.open(hyps_csv), index_col=0) for hyps_csv in hyps_list]

    return sl_dfs, me_dfs, db_dfs, hyps_dfs
            
# def fetch_snowline_data(rgi_no: str):
#     """Fetch snowline and melt extent CSVs from Zenodo for a given glacier number."""
#     json_url = "https://zenodo.org/records/16956246/files/rgi_data_links.json?download=1"
#     response = requests.get(json_url)
#     response.raise_for_status()
#     rgi_index = response.json()  # dictionary: rgi_no to zip URL
#     rgi_key = (rgi_no + ".zip").strip()

#     # Get the URL for the specific glacier
#     try:
#         zip_name = rgi_index[rgi_key]
#     except KeyError:
#         st.write(f"Key not found: '{rgi_key}'")
#         return None, None, None, None, None
        
#     zip_url = f"https://zenodo.org/records/16956246/files/{zip_name}?download=1"

#     # Download the zip
#     response = requests.get(zip_url)
#     response.raise_for_status()
#     with zipfile.ZipFile(io.BytesIO(response.content)) as gzf:
#         glac_csvs = gzf.namelist()
#         st.write(glac_csvs)

#         sl_csvs = [f for f in glac_csvs if "snowline_elev_percentile" in f and "eos_corr" not in f and "eabin" not in f]
#         me_csvs = [f.replace("snowline", "melt_extent") for f in sl_csvs]
#         db_csvs = [f.replace("snowline_elev_percentile", "db_bin_mean") for f in sl_csvs]
#         hyps_csvs = [f.replace("snowline_elev_percentile", "hypsometry") for f in sl_csvs]
#         return sl_csvs, me_csvs, db_csvs, hyps_csvs


# ---------------- Main page ----------------
gdf = st.session_state.get("gdf", None)
query_params = st.query_params
rgi_no = query_params.get("rgi_no", None)

# Allow manual input
manual_input = st.text_input("Enter a glacier name or RGI number:")
if manual_input and gdf is not None:
    # Case-insensitive substring match on rgi_id or glac_name
    matches = gdf[
        gdf["rgi_id"].str.contains(manual_input, case=False, na=False) |
        gdf["glac_name"].str.contains(manual_input, case=False, na=False)
    ]

    if not matches.empty:
        if len(matches) == 1:
            # Single match → use directly
            rgi_id = matches.iloc[0]["rgi_id"]
            st.success(f"Matched glacier: {rgi_id} (Name: {matches.iloc[0]['glac_name']})")
        else:
            # Multiple matches → show a selectbox popup
            st.info(f"Found {len(matches)} possible matches. Please choose one:")
            selected = st.selectbox(
                "Select a glacier:",
                matches["rgi_id"],
                format_func=lambda rid: f"{rid} – {matches.loc[matches['rgi_id']==rid, 'glac_name'].values[0]}"
            )
            if selected:
                rgi_id = selected
        rgi_no = "01." + rgi_id[-5:]
    else:
        st.error("No matching glacier found.")
          
if rgi_no is None:
    # st.warning("No glacier selected. Go back to the map and click a glacier.")
    st.page_link("app.py", label="No glacier selected. Go back to the map and click a glacier.")
else:
    # Convert RGI ID → RGI number (your convention: 01.xxxxx)
    st.write(f"### Data for RGI v7: {rgi_no}")
    sl_dfs, me_dfs, db_dfs, hyps_dfs = fetch_snowline_data(rgi_no)

    if sl_csvs is None:
        st.error("No snowline data found for this glacier.")
    else:
        for sl_df, me_df, db_df, hyps_df in zip(sl_dfs, me_dfs, db_dfs, hyps_dfs):
            glac_zbins_center = np.array(hyps_df.index.tolist())
            glac_bin_sizes = np.diff(glac_zbins_center)
            glac_bin_halfsize = glac_bin_sizes[0]/2
            binned_area = np.array(hyps_df.iloc[:, 0].tolist())
            set_ymin, set_ymax = glac_zbins_center[0]-glac_bin_halfsize, glac_zbins_center[-1]+glac_bin_halfsize

            dates = np.array(db_df.columns.tolist()).astype('datetime64[ns]')
            glac_binned_data = np.array(db_df.to_numpy())
        
            dates_per = np.array(me_df.index.tolist()).astype('datetime64[ns]')
            me_elev_per = np.array(me_df.iloc[:, 0].tolist())
            dates_sl_per = np.array(sl_df.index.tolist()).astype('datetime64[ns]')
            sl_elev_per = np.array(sl_df.iloc[:, 0].tolist())

            # ---------------- Plot ----------------
            st.write(f"### Plot for {sl_csv}")
            fig = plot_db_heatmap(db_bin=glac_binned_data,  dates=dates, bins_center=glac_zbins_center,
                                  binned_area=binned_area, set_ymin=set_ymin, set_ymax=set_ymax,
                                  glacno=selected_id, figsize=(12, 4), 
                                  line_plot=[(dates_per, me_elev_per, 'k', '-', 0.7, 'Melt extent'),
                                             (dates_per, sl_elev_per, 'k', '-.', 0.7, 'Snowline')])
            st.pyplot(fig)

