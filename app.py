import streamlit as st
import pdfplumber
import pytesseract
from pdf2image import convert_from_path
import tempfile
import os
import base64

st.set_page_config(
    page_title="PDF Text Extractor",
    page_icon="📄",
    layout="wide"
)

def extract_text_with_pdfplumber(pdf_path):
    text = ""
    try:
        with pdfplumber.open(pdf_path) as pdf:
            for page in pdf.pages:
                page_text = page.extract_text()
                if page_text:
                    text += page_text + "\n\n"
    except Exception as e:
        st.error(f"Error with pdfplumber: {e}")
    return text

def extract_text_with_tesseract(pdf_path, language='eng'):
    text = ""
    try:
        # Create a temporary directory to store images
        with tempfile.TemporaryDirectory() as path:
            # Convert PDF to images
            images = convert_from_path(pdf_path, dpi=300, output_folder=path)
            
            # Process each page
            for i, image in enumerate(images):
                with st.spinner(f"Processing page {i+1}/{len(images)}..."):
                    # Use pytesseract to extract text
                    config = f'--psm 6 --oem 3'
                    page_text = pytesseract.image_to_string(image, lang=language, config=config)
                    text += page_text + "\n\n"
    except Exception as e:
        st.error(f"Error with Tesseract OCR: {e}")
    return text

def get_download_link(text, filename="extracted_text.txt"):
    """Generates a link to download the text as a file"""
    b64 = base64.b64encode(text.encode()).decode()
    href = f'<a href="data:file/txt;base64,{b64}" download="{filename}">Download extracted text as TXT file</a>'
    return href

def main():
    st.title("📄 PDF Text Extractor")
    
    st.markdown("""
    This app extracts text from PDF documents with support for multiple languages including Bengali.
    Upload your PDF file below to get started.
    """)
    
    # File uploader
    uploaded_file = st.file_uploader("Upload your PDF file", type="pdf")
    
    # Settings
    with st.expander("Extraction Settings"):
        extraction_method = st.radio(
            "Choose extraction method:",
            ["pdfplumber (for standard PDFs)", "Tesseract OCR (better for scanned documents and non-Latin scripts)"]
        )
        
        if "Tesseract" in extraction_method:
            language = st.selectbox(
                "Select language:",
                ["eng (English)", "ben (Bengali)", "hin (Hindi)", "eng+ben (English & Bengali)"]
            )
            language_code = language.split(" ")[0]
        else:
            language_code = "eng"
    
    if uploaded_file is not None:
        # Save the uploaded file to a temporary file
        with tempfile.NamedTemporaryFile(delete=False, suffix='.pdf') as tmp_file:
            tmp_file.write(uploaded_file.getvalue())
            pdf_path = tmp_file.name
        
        col1, col2 = st.columns(2)
        
        with col1:
            st.subheader("PDF Preview")
            try:
                # Display the first page as preview
                images = convert_from_path(pdf_path, dpi=300, first_page=1, last_page=1)
                if images:
                    st.image(images[0], use_column_width=True)
            except Exception as e:
                st.error(f"Error previewing PDF: {e}")
        
        # Extract text based on selected method
        with st.spinner("Extracting text... This may take a while depending on the PDF size and complexity."):
            if "pdfplumber" in extraction_method:
                extracted_text = extract_text_with_pdfplumber(pdf_path)
            else:  # Tesseract OCR
                extracted_text = extract_text_with_tesseract(pdf_path, language_code)
        
        with col2:
            st.subheader("Extracted Text")
            if extracted_text:
                # Text area for displaying and editing extracted text
                text_output = st.text_area("", extracted_text, height=500)
                
                # Download button
                st.markdown(get_download_link(text_output), unsafe_allow_html=True)
                
                # Copy to clipboard button
                st.button("Copy to clipboard", help="Copy the extracted text to clipboard")
            else:
                st.warning("No text was extracted from the PDF. Try changing the extraction method or check if the PDF contains extractable text.")
        
        # Clean up the temporary file
        try:
            os.unlink(pdf_path)
        except:
            pass
    
    # Footer
    st.markdown("---")
    st.markdown("""
    #### Tips for better extraction:
    - Use **pdfplumber** for PDFs with digital text
    - Use **Tesseract OCR** for scanned documents or documents with non-Latin scripts
    - Higher quality scans will yield better OCR results
    - Make sure you have the appropriate language packages installed for Tesseract
    """)

if __name__ == "__main__":
    main()
