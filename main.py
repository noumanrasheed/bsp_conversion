import streamlit as st
import pdfplumber
import pandas as pd
import re
from io import BytesIO
import streamlit.components.v1 as components
from streamlit.components.v1 import html



# Google AdSense ad code
adsense_ad = """
<script async src="https://pagead2.googlesyndication.com/pagead/js/adsbygoogle.js?client=ca-pub-7227469495285542"
     crossorigin="anonymous"></script>
# <ins class="adsbygoogle"
#         style="display:block"
#         data-ad-client="ca-pub-7227469495285542"
#         data-ad-format="auto"
#         data-adtest="on"
#         data-full-width-responsive="true">
#     </ins>
<script>
(adsbygoogle = window.adsbygoogle || []).push({});
</script>
"""

# Render the ad in an iframe
components.iframe(adsense_ad, width=728, height=90)
# html(adsense_ad, height=100, width=300, unsafe_allow_html=True)


def extract_words(line):
    words = line.split()
    if len(words) >= 4:
        return words[0], words[1], words[2], words[6], words[-1]
    elif len(words) == 3:
        return words[2], '', words[-1]
    elif len(words) == 2:
        return '', '', words[-1]
    else:
        return '', '', ''

def pdf_to_dataframe(pdf_file):
    skip_phrases = [
        "FCAGBILLDET", "AGENT BILLING DETAILS", "27-3 1143 2 FLAIR ( PVT ) LTD",
        "Document Issue NR", "Transaction FARE", "Taxes, Fees & Charges",
        "COBL --STD Comm--", "--SUPP Comm--", "Tax on Balance",
        "AIR TRNC", "Number Date", "CPUI Code", "STAT FOP", "Amount",
        "Rate Amt", "Comm Payable", "TAX F&C", "PEN Amount", "SCOPE COMBINED", "*** ISSUES"
    ]

    exclude_start_words = [
        "REFUNDS TOTAL", "ISSUES", "REFUNDS", "GRAND TOTAL", "SCOPE COMBINED", "*** ISSUES", "MEMOS"
    ]

    date_page_pattern = re.compile(r'\d{2}-[A-Z]{3}-\d{4} \d{2}:\d{2}:\d{2}[APM]{2} Page : \d{5}')

    stop_processing = False

    with pdfplumber.open(pdf_file) as pdf:
        text_data = []

        # Start processing from the second page (index 1)
        for page_num, page in enumerate(pdf.pages[1:], start=2):
            text = page.extract_text()

            if text:
                for line in text.splitlines():
                    if "*** REFUNDS" in line:
                        stop_processing = True
                        break

                    if stop_processing:
                        break

                    if (not any(phrase in line for phrase in skip_phrases) and
                        not date_page_pattern.search(line) and
                        not any(line.startswith(word) for word in exclude_start_words) and
                        len(line.split()) > 2 and
                        not line.strip().startswith("+")):

                        # Extract the 3rd, 4th, and last words
                        word1, word2, word3, word4, last_word = extract_words(line)
                        text_data.append({
                            'Air': str(word1).zfill(3),
                            'TRNC': word2,
                            'Document Number': word3,
                            'FOP1': word4,
                            'FOP': word4,
                            'Balance Payable': last_word
                        })

        # Convert to a DataFrame
        df = pd.DataFrame(text_data)

        # Handle missing or inconsistent data
        df.fillna('', inplace=True)  # Fill NaN with empty strings
        df.dropna(how='all', inplace=True)  # Drop rows where all elements are NaN

    return df

def save_to_csv(df):
    df['Air']=df['Air'].astype(int)
    # Create 3 and 12 empty columns
    empty_columns_3 = ['Empty1', 'Empty2', 'Empty3']
    empty_columns_12 = [f'Empty{i}' for i in range(4, 16)]

    # Add empty columns to the DataFrame with empty string values
    for col in empty_columns_3 + empty_columns_12:
        df[col] = ''

    columns = list(df.columns)

    # Rebuild the column order as per the requirements
    reordered_columns = (
        columns[:3] +  # First 3 columns
        empty_columns_3 +  # 3 blank columns
        columns[3:5] +  # Next 2 columns
        empty_columns_12 +  # 12 blank columns
        columns[5:]  # Remaining columns
    )

    # Reorder DataFrame based on the new column order
    df = df[reordered_columns]

    # Save to CSV
    csv_data = df.to_csv(index=False, encoding='utf-8')
    return csv_data

def main():
    st.title("BSP PDF to CSV Converter")
    # st.write("Upload your PDF file:")

    pdf_file = st.file_uploader("Choose a PDF file", type="pdf")

    if pdf_file:
        df = pdf_to_dataframe(pdf_file)
        csv_data = save_to_csv(df)

        st.write("Conversion successful!")
        st.download_button("Download CSV", data=csv_data, file_name=f"{pdf_file.name.split('.')[0]}_converted.csv")

if __name__ == "__main__":
    main()
