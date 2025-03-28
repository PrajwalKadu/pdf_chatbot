from flask import Flask, render_template, request, jsonify, Response
import os
import PyPDF2
import faiss
import numpy as np
from sentence_transformers import SentenceTransformer, util

app = Flask(__name__)

UPLOAD_FOLDER = 'uploads'
if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER)

app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

# Load AI Model (Better Accuracy)
model = SentenceTransformer("multi-qa-mpnet-base-dot-v1")  # Improved model

# Global storage for FAISS and texts
index = None
doc_texts = []


def extract_text_from_pdf(pdf_path):
    """Extract text from a PDF file."""
    text = ""
    try:
        with open(pdf_path, "rb") as file:
            reader = PyPDF2.PdfReader(file)
            for page in reader.pages:
                text += page.extract_text() + "\n"
    except Exception as e:
        print(f"Error reading PDF: {e}")
    return text


def chunk_text(text, chunk_size=300):
    """Break text into smaller, meaningful chunks."""
    words = text.split()
    chunks = [" ".join(words[i:i + chunk_size]) for i in range(0, len(words), chunk_size)]
    return chunks


def build_faiss_index(texts):
    """Build FAISS index with sentence embeddings."""
    global index, doc_texts
    doc_texts = texts
    embeddings = model.encode(texts, normalize_embeddings=True)
    d = embeddings.shape[1]
    index = faiss.IndexFlatIP(d)  # Use Inner Product for better matching
    index.add(np.array(embeddings, dtype=np.float32))


@app.route('/')
def home():
    return render_template('index.html')


@app.route('/upload', methods=['POST'])
def upload_file():
    """Handles PDF upload, extracts text, and builds an index."""
    global index, doc_texts

    if 'file' not in request.files:
        return jsonify({'error': 'No file uploaded'})

    file = request.files['file']
    if file.filename == '':
        return jsonify({'error': 'No file selected'})

    filepath = os.path.join(app.config['UPLOAD_FOLDER'], file.filename)
    file.save(filepath)

    # Extract text and create FAISS index
    pdf_text = extract_text_from_pdf(filepath)
    if not pdf_text.strip():
        return jsonify({'error': 'Failed to extract text from PDF'})

    chunks = chunk_text(pdf_text)
    build_faiss_index(chunks)

    return jsonify({'message': 'PDF uploaded and processed successfully'})


@app.route('/ask', methods=['POST'])
def ask_question():
    """Handles question queries and retrieves the most relevant answer."""
    global index, doc_texts

    if index is None:
        return jsonify({'error': 'No PDF uploaded. Please upload a file first.'})

    data = request.get_json()
    question = data.get('question', '')

    if not question.strip():
        return jsonify({'error': 'Question cannot be empty'})

    # Encode question
    question_embedding = model.encode([question], normalize_embeddings=True)

    # Search in FAISS
    D, I = index.search(np.array(question_embedding, dtype=np.float32), k=5)

    # Retrieve best-matching answers
    best_answers = [doc_texts[i] for i in I[0] if i < len(doc_texts)]

    # Re-rank results for highest relevance
    best_answers_sorted = sorted(best_answers, key=lambda x: util.dot_score(question_embedding, model.encode([x],
                                                                                                             normalize_embeddings=True)).item(),
                                 reverse=True)

    # Pick the most relevant answer
    final_answer = best_answers_sorted[
        0] if best_answers_sorted else "Sorry, I couldn't find an answer in the document."

    def stream_response():
        for word in final_answer.split():
            yield word + " "

    return Response(stream_response(), content_type='text/plain')


if __name__ == '__main__':
    app.run(debug=True)
