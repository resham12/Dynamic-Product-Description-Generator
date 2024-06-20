import streamlit as st
import os
import tempfile
import fitz  # PyMuPDF
import openai
import csv
from reportlab.lib.pagesizes import A4
from reportlab.platypus import Paragraph
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.pdfgen import canvas
from fpdf import FPDF
from docx import Document
import io

# Set up temporary directory for file storage
temp_dir = tempfile.gettempdir()
main_pdf_path = os.path.join(temp_dir, "main_product.pdf")
competitor_pdf_path = os.path.join(temp_dir, "competitor_product.pdf")

# Initialize session state variables
if 'api_key' not in st.session_state:
    st.session_state.api_key = ""
if 'review_analysis' not in st.session_state:
    st.session_state.review_analysis = ""
if 'competitor_review_analysis' not in st.session_state:
    st.session_state.competitor_review_analysis = ""

# Set up OpenAI API key
openai.api_key = st.session_state.api_key

def extract_text_from_pdf(pdf_path):
    """Extract text content from a PDF file."""
    text = ""
    with fitz.open(pdf_path) as doc:
        for page in doc:
            text += page.get_text()
    return text

def analyze_reviews(content, chunk_size=3000):
    """Analyze product reviews using OpenAI's GPT-4 model."""
    # Split content into chunks to handle large amounts of text
    chunks = [content[i:i+chunk_size] for i in range(0, len(content), chunk_size)]
    all_analyses = []

    # Analyze each chunk
    for chunk in chunks:
        response = openai.chat.completions.create(
            model="gpt-4o",
            messages=[
                {"role": "system", "content": "You are an assistant that deeply analyzes Amazon reviews. Provide your analysis in a structured format with sections for positive keywords, negative keywords, positive attributes, negative attributes, and a brief summary."},
                {"role": "user", "content": f"Analyze these reviews and identify positive and negative keywords and attributes: {chunk}"}
            ]
        )
        all_analyses.append(response.choices[0].message.content)

    # Combine all analyses
    combined_analysis = "\n\n".join(all_analyses)

    # Generate a final summary of all analyses
    final_summary_response = openai.chat.completions.create(
        model="gpt-4o",
        messages=[
            {"role": "system", "content": "You are an assistant that summarizes multiple review analyses into a single comprehensive report."},
            {"role": "user", "content": f"Summarize these review analyses into a single comprehensive report with sections for positive keywords, negative keywords, positive attributes, negative attributes, and an overall conclusion. Avoid repetition and provide a clear, concise summary:\n\n{combined_analysis}"}
        ]
    )

    return final_summary_response.choices[0].message.content

def generate_keywords_and_descriptions(review_analysis):
    """Generate keywords and product descriptions based on review analysis."""
    # Generate keyword suggestions
    keyword_response = openai.chat.completions.create(
        model="gpt-4o",
        messages=[
            {"role": "system", "content": "You are an assistant that suggests keywords for Amazon product titles and descriptions."},
            {"role": "user", "content": f"Based on this review analysis, suggest recommended keywords that should be used in product titles and descriptions to attract more customers: {review_analysis}"}
        ]
    )

    # Generate product descriptions
    description_response = openai.chat.completions.create(
        model="gpt-4o",
        messages=[
            {"role": "system", "content": "You are an assistant that generates dynamic product descriptions."},
            {"role": "user", "content": f"Generate 3 dynamic product descriptions based on this review analysis. Keep the descriptions short, informative, and attractive to customers. Do not include keyword suggestions, just the descriptions: {review_analysis}"}
        ]
    )

    # Format keywords and descriptions for display
    keywords = keyword_response.choices[0].message.content.split("\n")
    descriptions = description_response.choices[0].message.content.split("\n")
    formatted_keywords = "\n".join(f"- {keyword}" for keyword in keywords)
    formatted_descriptions = "\n".join(f"- {description}" for description in descriptions)

    return formatted_keywords, formatted_descriptions

def analyze_competitor(content, chunk_size=3000):
    """Analyze competitor product reviews using OpenAI's GPT-4 model."""
    # Similar to analyze_reviews, but focused on competitor analysis
    chunks = [content[i:i+chunk_size] for i in range(0, len(content), chunk_size)]
    all_analyses = []

    for chunk in chunks:
        response = openai.chat.completions.create(
            model="gpt-4o",
            messages=[
                {"role": "system", "content": "You are an assistant that deeply analyzes competitor product reviews. Provide your analysis in a structured format with sections for positive keywords, negative keywords, positive attributes, negative attributes, and a brief summary."},
                {"role": "user", "content": f"Analyze these competitor reviews and identify positive and negative keywords and attributes: {chunk}"}
            ]
        )
        all_analyses.append(response.choices[0].message.content)

    combined_analysis = "\n\n".join(all_analyses)

    final_summary_response = openai.chat.completions.create(
        model="gpt-4o",
        messages=[
            {"role": "system", "content": "You are an assistant that summarizes multiple competitor review analyses into a single comprehensive report."},
            {"role": "user", "content": f"Summarize these competitor review analyses into a single comprehensive report with sections for positive keywords, negative keywords, positive attributes, negative attributes, and an overall conclusion. Focus on insights that could be used for competitive positioning. Avoid repetition and provide a clear, concise summary:\n\n{combined_analysis}"}
        ]
    )

    return final_summary_response.choices[0].message.content

def csv_to_pdf(csv_file, pdf_file):
    """Convert CSV file to PDF format."""
    pdf = canvas.Canvas(pdf_file, pagesize=A4)
    page_width, page_height = A4
    styles = getSampleStyleSheet()
    normal_style = styles["BodyText"]

    with open(csv_file, 'r', encoding='utf-8') as csvfile:
        reader = csv.reader(csvfile)
        y = page_height - 50  # Start from the top with a margin of 50
        for row in reader:
            text = ", ".join(row)
            paragraph = Paragraph(text, normal_style)
            w, h = paragraph.wrap(page_width - 100, page_height)
            paragraph.drawOn(pdf, 50, y - h)
            y -= h + 15  # Move down to the next line
            if y < 50:
                pdf.showPage()
                y = page_height - 50
        pdf.save()

def home_screen():
    """Render the home screen of the Streamlit app."""
    st.title('Welcome to Dynamic Product Description Generator')
    st.write('Please enter your OpenAI API key to proceed.')
    st.session_state.api_key = st.text_input('OpenAI API Key', type='password')
    if st.button('Save API Key'):
        if st.session_state.api_key:
            st.success('API Key saved successfully!')
            st.session_state.api_key_saved = True
        else:
            st.error('Please enter a valid API key.')
    if st.session_state.api_key_saved:
        if st.button('Go to Main Screen'):
            st.session_state.screen = 'main'

def create_word_doc(text, file_name):
    """Create a Word document with the given text."""
    doc = Document()
    doc.add_paragraph(text)
    doc.save(file_name)

def render_download_options(output, output_type):
    """Render download options for generated content."""
    word_file = f"{output_type}.docx"
    create_word_doc(output, word_file)
    with open(word_file, "rb") as f:
        st.download_button(f"Download {output_type} as Word Document", f, file_name=word_file)

def main_screen():
    """Render the main screen of the Streamlit app."""
    st.title('Dynamic Product Description Generator')

    # File uploaders for main and competitor products
    uploaded_file = st.file_uploader("Select a CSV file for main product:", type=["csv"])
    uploaded_competitor_file = st.file_uploader("Select a CSV file for competitor product (optional):", type=["csv"])

    # Main product analysis
    if uploaded_file and st.button("Analyze Reviews"):
        main_csv_path = os.path.join(temp_dir, "main_product.csv")
        with open(main_csv_path, "wb") as f:
            f.write(uploaded_file.getbuffer())

        csv_to_pdf(main_csv_path, main_pdf_path)
        main_review_content = extract_text_from_pdf(main_pdf_path)
        st.session_state.review_analysis = analyze_reviews(main_review_content)
        st.write("Review Analysis:", st.session_state.review_analysis)
        render_download_options(st.session_state.review_analysis, "Review_Analysis")

    # Generate keywords and descriptions
    if st.session_state.review_analysis:
        if st.button("Generate Keywords and Descriptions"):
            user_keywords, user_descriptions = generate_keywords_and_descriptions(st.session_state.review_analysis)
            st.session_state.keywords_and_descriptions = f"Keyword Recommendations:\n\n{user_keywords}\n\nDynamic Descriptions:\n\n{user_descriptions}"
            st.write("Keyword Recommendations:", user_keywords)
            st.write("Dynamic Descriptions:", user_descriptions)
            render_download_options(st.session_state.keywords_and_descriptions, "Keywords_and_Descriptions")

        # Generate optimized titles and descriptions
        if st.button("Generate Optimized Titles and Descriptions"):
            optimized_content = openai.chat.completions.create(
                model="gpt-4o",
                messages=[
                    {"role": "system", "content": "You are an assistant that optimizes product titles and descriptions for e-commerce platforms."},
                    {"role": "user", "content": f"Based on these keywords and descriptions, create 3 optimized product titles and descriptions. Ensure compliance with platform restrictions on title length and keyword usage:\n\n{st.session_state.keywords_and_descriptions}"}
                ]
            )
            optimized_content_text = optimized_content.choices[0].message.content
            st.write("Optimized Titles and Descriptions:", optimized_content_text)
            render_download_options(optimized_content_text, "Optimized_Titles_and_Descriptions")

        # Generate review summary
        if st.button("Generate Review Summary"):
            review_summary = openai.chat.completions.create(
                model="gpt-4o",
                messages=[
                    {"role": "system", "content": "You are an assistant that summarizes product review insights."},
                    {"role": "user", "content": f"Provide a concise overview of what customers are saying about the product. Summarize positive and negative attributes, highlighting key features and potential improvements:\n\n{st.session_state.review_analysis}"}
                ]
            )
            review_summary_text = review_summary.choices[0].message.content
            st.write("Summarized Review Insights:", review_summary_text)
            render_download_options(review_summary_text, "Review_Summary")

    # Competitor analysis
    if uploaded_competitor_file:
        competitor_csv_path = os.path.join(temp_dir, "competitor_product.csv")
        with open(competitor_csv_path, "wb") as f:
            f.write(uploaded_competitor_file.getbuffer())

        csv_to_pdf(competitor_csv_path, competitor_pdf_path)
        competitor_review_content = extract_text_from_pdf(competitor_pdf_path)
        
        if st.button("Analyze Competitor"):
            st.session_state.competitor_review_analysis = analyze_competitor(competitor_review_content)
            st.write("Competitor Review Analysis:", st.session_state.competitor_review_analysis)
            render_download_options(st.session_state.competitor_review_analysis, "Competitor_Review_Analysis")

            # Generate competitive edge insights
            competitive_edge_insights = openai.chat.completions.create(
                model="gpt-4o",
                messages=[
                    {"role": "system", "content": "You are an assistant that provides competitive edge insights based on competitor review analysis."},
                    {"role": "user", "content": f"Based on this competitor review analysis, provide insights on successful keywords, descriptions, and strategies for competitive positioning. Focus on benchmarking and identifying areas for improvement:\n\n{st.session_state.competitor_review_analysis}"}
                ]
            )
            competitive_edge_text = competitive_edge_insights.choices[0].message.content
            st.write("Competitive Edge Insights:", competitive_edge_text)
            render_download_options(competitive_edge_text, "Competitive_Edge_Insights")

    # Reset button to clear generated content
    if st.button("Reset"):
        st.session_state.review_analysis = ""
        st.session_state.keywords_and_descriptions = ""
        st.session_state.competitor_review_analysis = ""
        st.session_state.competitor_insights = ""
        st.success("Generated content cleared successfully.")

# Manage screen navigation
if 'screen' not in st.session_state:
    st.session_state.screen = 'home'
if 'api_key_saved' not in st.session_state:
    st.session_state.api_key_saved = False

# Display appropriate screen based on session state
if st.session_state.screen == 'home':
    home_screen()
elif st.session_state.screen == 'main' and st.session_state.api_key_saved:
    main_screen()
else:
    st.error('Please save your API key to proceed to the main screen.')