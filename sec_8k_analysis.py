import requests
import pandas as pd
import json
import xml.etree.ElementTree as ET
import spacy
from bs4 import BeautifulSoup

# Setup
HEADERS = {"User-Agent": "David Rodriguez da005078@ucf.edu"}  # Personalized to avoid being blocked
TICKER_JSON_URL = "https://www.sec.gov/files/company_tickers.json"
BASE_ATOM_URL = "https://www.sec.gov/cgi-bin/browse-edgar?action=getcompany&CIK={cik}&type=8-K&count={count}&output=atom"
MAX_DOCS = 100  # Para extracción completa

# Load spacy NER model
nlp = spacy.load("en_core_web_sm")


# Get CIKs from the S&P500 tickers list
def get_sp500_tickers():
    try:
        print("Fetching company tickers from SEC...")
        res = requests.get(TICKER_JSON_URL, headers=HEADERS, timeout=10)
        data = res.json()
        print("Tickers loaded successfully!")
        # Create a map for company names
        tickers_map = {v["ticker"]: (v["cik_str"], v["title"]) for v in data.values()}
        return tickers_map
    except Exception as e:
        print(f"Error fetching tickers: {e}")
        return {}


# Function to clean HTML tags
def clean_html(raw_text):
    if raw_text:
        soup = BeautifulSoup(raw_text, "html.parser")
        return soup.get_text()
    return ""


# Function to extract data from 8-K filings
def extract_8k_data(cik, company_name):
    url = BASE_ATOM_URL.format(cik=cik, count=MAX_DOCS)

    try:
        print(f"Fetching 8-K data for CIK {cik}...")
        res = requests.get(url, headers=HEADERS, timeout=10)

        # Handle potential parsing errors
        try:
            root = ET.fromstring(res.content)
        except ET.ParseError as e:
            print(f"Error parsing XML for CIK {cik}: {e}")
            return []

        extracted_data = []
        for entry in root.findall("{http://www.w3.org/2005/Atom}entry"):
            filing_time = entry.find("{http://www.w3.org/2005/Atom}updated").text

            # Clean HTML from the summary
            summary = entry.find("{http://www.w3.org/2005/Atom}summary").text
            clean_summary = clean_html(summary)

            # Use NER to extract product mentions
            doc = nlp(clean_summary)

            product_name = ""
            product_desc = clean_summary[:180] if clean_summary else ""  # Limit to 180 characters

            for ent in doc.ents:
                if ent.label_ == "PRODUCT":
                    product_name = ent.text
                    break

            extracted_data.append({
                "company_name": company_name,
                "filing_time": filing_time,
                "new_product": product_name if product_name else "",  # Leave blank if no product found
                "product_description": product_desc
            })

        print(f"Successfully processed CIK {cik}!")
        return extracted_data

    except requests.exceptions.Timeout:
        print(f"Request for CIK {cik} timed out.")
        return []

    except Exception as e:
        print(f"Error processing CIK {cik}: {e}")
        return []


# Main function
def main():
    tickers = get_sp500_tickers()
    all_data = []

    # Limit the number of tickers for faster testing (comment out after testing)
    limited_tickers = {k: tickers[k] for k in list(tickers)[:5]}

    for ticker, (cik, company_name) in limited_tickers.items():
        print(f"Processing ticker: {ticker} (CIK: {cik})")
        try:
            data = extract_8k_data(cik, company_name)
            for item in data:
                item["stock_name"] = ticker
                all_data.append(item)
        except Exception as e:
            print(f"Error processing {ticker}: {e}")

    # Save to CSV
    if all_data:
        print("Saving data to CSV...")
        df = pd.DataFrame(all_data)
        df.to_csv("extracted_data.csv", index=False)
        print("Data extraction complete!")
    else:
        print("No data extracted.")


if __name__ == "__main__":
    main()

