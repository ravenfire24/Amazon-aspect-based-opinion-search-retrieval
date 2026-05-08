# Amazon Semantic Aspect-Based Review Intelligence System

An NLP-powered review analysis platform that combines semantic search, aspect-based sentiment analysis (ABSA), and explainable AI for large-scale product review retrieval.

---

## Live Demo


## Features

- Semantic search using SentenceTransformers + FAISS
- Aspect-based sentiment analysis (ABSA)
- Context-aware transformer sentiment classification
- Explainable sentiment predictions with confidence scores
- Interactive Streamlit dashboard
- PDF report generation
- Optimized for large datasets (50k+ reviews)

---

## Tech Stack

- Python
- Streamlit
- FAISS
- SentenceTransformers
- Hugging Face Transformers
- spaCy
- Plotly
- ReportLab

---

## System Pipeline

```text
User Query
   ↓
Semantic Embedding
   ↓
FAISS Retrieval
   ↓
Aspect Extraction
   ↓
Contextual Sentiment Analysis
   ↓
Interactive Dashboard + PDF Export
```

---

## Installation

### Clone Repository

```bash
git clone https://github.com/ravenfire24/Amazon-aspect-based-opinion-search-retrieval
cd Amazon-aspect-based-opinion-search-retrieval
```

### Install Dependencies

```bash
pip install -r requirements.txt
```

### Download spaCy Model

```bash
python -m spacy download en_core_web_sm
```

---

## Run Application

```bash
 python -m streamlit run app.py 
```

---

## Example Queries

```text
battery issues
screen quality
charging problems
camera performance
```

---

## Project Structure

```text
├── app.py
├── semantic_search.py
├── aspect_extraction.py
├── preprocessing.py
├── evaluation.py
├── bert_classifier.py
├── train_model.py
├── requirements.txt
└── README.md
```

---

## Highlights

- Semantic retrieval instead of keyword matching
- Contextual aspect-level sentiment analysis
- Persistent FAISS indexing for fast startup
- Batched NLP processing with `nlp.pipe()`
- Explainable NLP outputs with confidence scoring

---
![alt text]()
