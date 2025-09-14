
import streamlit as st
import pandas as pd
from tender import scrape_all_sites, SITES
from bs4 import BeautifulSoup

st.set_page_config(page_title="Universal Tender Scraper", layout="wide")
st.title("📑 Universal Government Tender Scraper")

# -----------------------------
# Sidebar filters
# -----------------------------
st.sidebar.header("🔍 Filters")
states = st.sidebar.multiselect("Select States", [s["name"] for s in SITES])
keywords_input = st.sidebar.text_input("Keyword(s) (use OR for multiple, e.g., Solar OR Irrigation)")
start_date = st.sidebar.date_input("Start Date", value=None)
end_date = st.sidebar.date_input("End Date", value=None)
headless = st.sidebar.checkbox("Run browser in background (headless)", value=False)

# -----------------------------
# Search button
# -----------------------------
if st.sidebar.button("Search Tenders"):
    st.info("⏳ Please wait... Open browser, solve CAPTCHA for each state, then press ENTER in terminal or Streamlit will wait automatically.")

    # Split multiple keywords
    keywords = [k.strip().lower() for k in keywords_input.split("OR")] if keywords_input else None

    # Scrape
    df = scrape_all_sites(
        keyword=None,  # will filter manually below
        start_date=start_date if start_date else None,
        end_date=end_date if end_date else None,
        states=states if states else None,
        headless=headless
    )

    if df.empty:
        st.error("No tenders found.")
    else:
        # Multi-keyword filtering
        if keywords:
            mask = df.apply(lambda row: any(k in " ".join([str(c) for c in row if isinstance(c, str)]).lower() for k in keywords), axis=1)
            df = df[mask]

        if df.empty:
            st.error("No tenders matched your keywords/filters.")
        else:
            # Make title column clickable if Link exists
            if "Col5" in df.columns:
                df["Title"] = df.apply(lambda x: f'<a href="{x["Link"]}" target="_blank">{BeautifulSoup(str(x["Col5"]), "html.parser").get_text()}</a>' if x.get("Link") else BeautifulSoup(str(x["Col5"]), "html.parser").get_text(), axis=1)

            st.write(f"✅ {len(df)} tenders found")
            st.write(df.to_html(escape=False, index=False), unsafe_allow_html=True)

            # CSV download
            csv = df.to_csv(index=False)
            st.download_button("📥 Download Results (CSV)", csv, "tenders.csv", "text/csv")
