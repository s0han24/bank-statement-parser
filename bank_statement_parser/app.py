import streamlit as st
import pypdf
import easyocr
from google import genai
from google.genai import types
from pydantic import BaseModel, Field, ValidationError
import pandas as pd
import json
import io
import os
import fitz
import time
from validate import validate_dataframe
from regex_parser import parse_statement

# --- Configurations ---
st.set_page_config(page_title="Bank Statement Parser", layout="wide")

# Fallback to an environment variable or hardcoded placeholder
API_KEY = os.environ.get("GEMINI_API_KEY")



# --- Pydantic Schemas ---
class Transaction(BaseModel):
    date: str = Field(description="Transaction date in YYYY-MM-DD format if possible")
    description: str = Field(description="Description or narration of the transaction")
    amount: float = Field(description="Absolute amount of the transaction")
    type: str = Field(description="Either 'Credit' or 'Debit'")
    balance: float = Field(description="Account balance after the transaction, if available. 0.0 if unknown.")

class StatementSchema(BaseModel):
    opening_balance: float = Field(description="Opening balance of the statement period. 0.0 if unknown.")
    closing_balance: float = Field(description="Closing balance of the statement period. 0.0 if unknown.")
    transactions: list[Transaction] = Field(description="List of extracted transactions")

# --- Helper Functions ---
@st.cache_resource
def get_ocr_reader():
    return easyocr.Reader(['en'])

def extract_text(file_bytes, filename, ocr_engine="EasyOCR"):
    if filename.lower().endswith('.pdf'):
        try:
            reader = pypdf.PdfReader(io.BytesIO(file_bytes))
            text = ""
            for page in reader.pages:
                page_text = page.extract_text()
                if page_text:
                    text += page_text + "\n"
            
            if len(text.strip()) > 50:
                return text
            else:
                # Fallback: Rasterize and OCR if PDF is image-based
                doc = fitz.open(stream=file_bytes, filetype="pdf")
                full_text = ""
                
                if ocr_engine == "Tesseract":
                    import pytesseract
                    from PIL import Image
                else:
                    ocr_reader = get_ocr_reader()

                for page in doc:
                    pix = page.get_pixmap(dpi=150)
                    if ocr_engine == "Tesseract":
                        img = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)
                        page_text = pytesseract.image_to_string(img)
                        full_text += page_text + "\n"
                    else:
                        img_bytes = pix.tobytes("png")
                        result = ocr_reader.readtext(img_bytes, detail=0)
                        full_text += "\n".join(result) + "\n"
                return full_text
        except Exception as e:
            return f"Error reading PDF: {str(e)}"
    else:
        # Assume it's an image
        if ocr_engine == "Tesseract":
            import pytesseract
            from PIL import Image
            img = Image.open(io.BytesIO(file_bytes))
            return pytesseract.image_to_string(img)
        else:
            reader = get_ocr_reader()
            result = reader.readtext(file_bytes, detail=0)
            return "\n".join(result)

def call_gemini(text, error_hint=""):
    client = genai.Client(api_key=API_KEY)
    
    prompt = f"Extract all transactions and the opening/closing balances from this bank statement text:\n\n{text}"
    if error_hint:
        prompt += f"\n\nIMPORTANT - Fix these errors from previous attempt: {error_hint}"

    response = client.models.generate_content(
        model="gemini-3-flash-preview",
        contents=prompt,
        config=types.GenerateContentConfig(
            response_mime_type="application/json",
            response_schema=StatementSchema,
        ),
    )
    return response.text

def process_statement(text):
    error_hint = ""
    for attempt in range(3):
        try:
            raw_json = call_gemini(text, error_hint=error_hint)
            result = StatementSchema.model_validate_json(raw_json)
            return result, raw_json
        except ValidationError as e:
            error_hint = f"Previous attempt failed: {e}. Fix these fields."
            time.sleep(10)
        except Exception as e:
            error_hint = f"API Call failed: {e}."
            # Artificial delay between attempts to avoid hitting rate limits
            time.sleep(10)
    raise ValueError(f"Failed to parse statement after 3 attempts. {error_hint}")

# --- App Flow ---

if 'step' not in st.session_state:
    st.session_state.step = 1

def next_step():
    st.session_state.step += 1

def reset():
    for key in list(st.session_state.keys()):
        del st.session_state[key]
    st.session_state.step = 1

if st.session_state.step == 1:
    st.title("Bank Statement Parser Prototype")
    st.markdown("Upload a bank statement (PDF or Image) to extract transactions.")
    
    ocr_engine = st.selectbox("Select OCR Engine for Scanned Documents:", ["EasyOCR", "Tesseract"])
    st.session_state.ocr_engine = ocr_engine
    
    uploaded_file = st.file_uploader("Choose a file", type=["pdf"])
    if uploaded_file is not None:
        if st.button("Process Statement"):
            st.session_state.file_bytes = uploaded_file.read()
            st.session_state.filename = uploaded_file.name
            st.session_state.step = 2
            st.rerun()

elif st.session_state.step == 2:
    st.title("Processing Statement")
    
    with st.spinner('Extracting text from file...'):
        text = extract_text(st.session_state.file_bytes, st.session_state.filename, st.session_state.ocr_engine)
        st.session_state.extracted_text = text
    
    with st.expander("Show Raw Extracted Text (Debug)", expanded=False):
        st.text(st.session_state.extracted_text)
        
    with st.spinner('Parsing transactions with Gemini 2.5  Flash Lite...'):
        try:
            parsed_result, raw_json = process_statement(st.session_state.extracted_text)
            st.session_state.parsed_result = parsed_result
            st.session_state.raw_json = raw_json
            st.session_state.step = 3
            st.rerun()
        except Exception as e:
            st.error(f"Failed to process statement: {e}")
            if st.button("Try Again"):
                reset()
                st.rerun()

elif st.session_state.step == 3:
    st.title("Review & Export")
    
    with st.expander("Show Raw Extracted Text (Debug)", expanded=False):
        st.text(st.session_state.extracted_text)
        
    result = st.session_state.parsed_result
    
    col1, col2, col3 = st.columns(3)
    col1.metric("Opening Balance", f"{result.opening_balance:,.2f}")
    col2.metric("Closing Balance", f"{result.closing_balance:,.2f}")
    
    net_flow = result.closing_balance - result.opening_balance
    col3.metric("Net Flow", f"{net_flow:,.2f}")
    
    st.subheader("Transactions")
    
    # Convert Pydantic models to a list of dicts for pandas
    tx_dicts = [tx.model_dump() for tx in result.transactions]
    if tx_dicts:
        df = pd.DataFrame(tx_dicts)
        edited_df = st.data_editor(df, width='stretch', num_rows="dynamic")
        
        st.subheader("Validation")
        val_res = validate_dataframe(edited_df)
        if "error" in val_res:
            st.error(val_res["error"])
        elif val_res.get("total_checks", 0) > 0:
            pct = val_res["pass_percentage"]
            if pct == 100:
                st.success(f"✅ {pct:.1f}% Pass Rate ({val_res['passed_checks']}/{val_res['total_checks']} checks passed)")
            else:
                st.warning(f"⚠️ {pct:.1f}% Pass Rate ({val_res['passed_checks']}/{val_res['total_checks']} checks passed)")
                with st.expander("Failed Checks"):
                    for f in val_res["failed_rows"]:
                        st.write(f"Row {f['index']}: Expected {f['expected']:.2f} but got {f['actual']:.2f} (Prev: {f['prev_bal']:.2f}, Tx: {f['amount']:.2f} {f['type']})")
        else:
            st.info("Not enough data to perform running balance checks.")
            
        st.divider()
        st.subheader("Strict Regex Validation")
        st.info("Note: This secondary validation fallback currently only works for standard **SBI Digital Statements**.")
        if st.button("Validate Output"):
            regex_txs = parse_statement(st.session_state.extracted_text)
            st.write(f"**Regex Extracted:** {len(regex_txs)} transactions")
            st.write(f"**LLM Extracted:** {len(edited_df)} transactions")
            
            if regex_txs:
                llm_records = edited_df.to_dict('records')
                matched_lines = 0
                min_len = min(len(regex_txs), len(llm_records))
                
                for i in range(min_len):
                    r_tx = regex_txs[i]
                    l_tx = llm_records[i]
                    
                    r_credit = float(r_tx.get('credit', 0.0))
                    r_debit = float(r_tx.get('debit', 0.0))
                    r_balance = float(r_tx.get('balance', 0.0))
                    
                    r_type = 'credit' if r_credit > 0 else 'debit'
                    r_amount = r_credit if r_credit > 0 else r_debit
                    
                    l_amount = float(l_tx.get('amount', 0.0))
                    l_type = str(l_tx.get('type', '')).strip().lower()
                    l_balance = float(l_tx.get('balance', 0.0))
                    
                    if abs(r_amount - l_amount) < 0.01 and r_type == l_type and abs(r_balance - l_balance) < 0.01:
                        matched_lines += 1
                        
                if matched_lines == max(len(regex_txs), len(llm_records)) and matched_lines > 0:
                    st.success(f"**Strict Alignment Matched Lines:** {matched_lines} (Perfect Match!)")
                else:
                    st.warning(f"**Strict Alignment Matched Lines:** {matched_lines} out of {max(len(regex_txs), len(llm_records))}.")
                
                st.dataframe(pd.DataFrame(regex_txs))
            else:
                st.warning("No transactions could be parsed via regex. Make sure this is an SBI statement format.")
                
    else:
        st.info("No transactions extracted.")
        edited_df = pd.DataFrame()

    st.subheader("Export")
    export_col1, export_col2 = st.columns(2)
    
    if not edited_df.empty:
        csv = edited_df.to_csv(index=False).encode('utf-8')
        export_col1.download_button(
            label="Download CSV",
            data=csv,
            file_name='transactions.csv',
            mime='text/csv',
        )
        
        json_str = edited_df.to_json(orient='records')
        export_col2.download_button(
            label="Download JSON",
            data=json_str,
            file_name='transactions.json',
            mime='application/json',
        )

    if st.button("Start Over"):
        reset()
        st.rerun()
