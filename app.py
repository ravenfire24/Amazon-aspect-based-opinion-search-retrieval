import streamlit as st
import pandas as pd
import plotly.express as px
import spacy
import torch
from io import BytesIO
from sentence_transformers import (
    SentenceTransformer,
    util
)
from transformers import (
    AutoTokenizer,
    AutoModelForSequenceClassification
)


from reportlab.platypus import (
    SimpleDocTemplate,
    Paragraph,
    Spacer
)

from reportlab.lib.styles import (
    getSampleStyleSheet
)

from semantic_search import SemanticSearch
from evaluation import precision_at_k
from aspect_extraction import extract_aspects


# LOAD SPACY MODEL


@st.cache_resource(
    show_spinner=False
)
def load_spacy_model():

    return spacy.load(
        "en_core_web_sm"
    )

nlp = load_spacy_model()


# PAGE CONFIG


st.set_page_config(
    page_title="Amazon NLP Retrieval System",
    layout="wide"
)


# LOAD TRANSFORMER MODEL


@st.cache_resource(
    show_spinner=False
)
def load_transformer_model():

    MODEL_NAME = (
        "cardiffnlp/twitter-roberta-base-sentiment-latest"
    )

    tokenizer = (
        AutoTokenizer.from_pretrained(
            MODEL_NAME
        )
    )

    model = (
        AutoModelForSequenceClassification
        .from_pretrained(MODEL_NAME)
    )
    
    model.eval()
    return tokenizer, model

tokenizer, model = (
    load_transformer_model()
)
@st.cache_resource(
    show_spinner=False
)
def load_aspect_model():

    return SentenceTransformer(
        'all-MiniLM-L6-v2'
    )

aspect_model = load_aspect_model()
PRODUCT_CONCEPTS = [

    "battery",
    "screen",
    "camera",
    "speaker",
    "charger",
    "performance",
    "design",
    "quality",
    "price",
    "product",
    "device",
    "phone",
    "laptop",
    "electronics",
    "feature"
]

@st.cache_resource(
    show_spinner=False
)
def load_product_embeddings():

    return aspect_model.encode(

        PRODUCT_CONCEPTS,

        convert_to_tensor=True
    )

product_embeddings = load_product_embeddings()

# BUILD CACHED SEARCH ENGINE


@st.cache_resource(
    show_spinner=False
)
def load_search_engine(
    file_path,
    text_column
):

    engine = SemanticSearch()

    engine.build_index(
        file_path,
        text_column
    )

    return engine


# SENTIMENT PREDICTION

def predict_sentiment(text):

    inputs = tokenizer(

        text,

        return_tensors="pt",

        truncation=True,

        padding=True
    )

    with torch.no_grad():

        outputs = model(**inputs)

    probabilities = torch.softmax(

        outputs.logits,

        dim=1
    )

    prediction = torch.argmax(

        probabilities,

        dim=1
    ).item()

    confidence = round(

        probabilities[0][prediction]
        .item(),

        2
    )
   

    sentiment_map = {

        0: 'negative',

        1: 'neutral',

        2: 'positive'
    }
    if confidence < 0.55:

        sentiment_map[prediction] = "neutral"

    return (
        sentiment_map[prediction],
        confidence
    )
    
@st.cache_data(
    show_spinner=False
)
def get_aspect_embedding(text):

    return aspect_model.encode(

        text,

        convert_to_tensor=True
    )


# ASPECT VALIDATION


def is_valid_aspect(chunk):

    root = chunk.root

    # Keep noun-based aspects only

    if root.pos_ not in [
        "NOUN",
        "PROPN"
    ]:
        return False

    # Important dependency roles
    if root.dep_ not in [

        "nsubj",
        "dobj",
        "pobj",
        "compound",
        "attr",
        "conj"
    ]:
        return False

    # Ignore weak tokens

    if (
        root.is_stop
        or root.is_punct
        or root.like_num
    ):
        return False

    # Ignore temporal / numeric entities

    if root.ent_type_ in [
        "DATE",
        "TIME",
        "CARDINAL",
        "ORDINAL"
    ]:
        return False

    # Ignore tiny tokens

    if len(root.text.strip()) < 3:
        return False

   

    
    # SEMANTIC PRODUCT RELEVANCE   

    aspect_text = chunk.text.lower()

    aspect_embedding = get_aspect_embedding(
        aspect_text
    )

    similarities = util.cos_sim(

        aspect_embedding,

        product_embeddings
    )

    max_similarity = similarities.max().item()

    # Require semantic product relevance

    if max_similarity < 0.55:
        return False

# REMOVE GENERIC BUSINESS TERMS


    generic_business_terms = {

        "product",
        "company",
        "item",
        "seller",
        "service"
    }

    if root.lemma_.lower() in generic_business_terms:
        return False




    

    return True

# ASPECT SENTIMENT ANALYSIS
def aspect_sentiment_analysis(doc):    

    aspect_sentiments = []

    seen = set()

    for chunk in doc.noun_chunks:

       
        # CLEAN ASPECT TOKENS     

        aspect_tokens = [

            token.lemma_.lower()

            for token in chunk

            if (

                token.pos_ in [
                    "NOUN",
                    "PROPN",
                    "ADJ"
                ]

                and not token.is_stop

                and not token.is_punct

                and token.is_alpha

                and len(token.text) > 2
            )
        ]

       
        # EMPTY ASPECT CHECK
      

        if not aspect_tokens:
            continue

        aspect = " ".join(
            aspect_tokens
        )

   
  
       
       
        # VALIDATE ASPECT
      

        if not is_valid_aspect(chunk):
            continue

        
        # REMOVE DUPLICATES
        

        if aspect in seen:
            continue 
     

       
        # CLEAN SENTENCE     

        sentence = (
            chunk.sent.text
            .replace("\\n", " ")
            .strip("'\" ")
        )

   
       
        # CONTEXT WINDOW
        

        sentence = chunk.sent.text.strip()

        context = sentence

       

      
        # FALLBACK LOCAL WINDOW
        

        if not context.strip():

            sentence_tokens = [

                token.text

                for token in chunk.sent

                if (
                    token.is_alpha
                    and not token.is_punct
                )
            ]

            aspect_index = (
                chunk.root.i
                - chunk.sent.start
            )

            start = max(
                0,
                aspect_index - 4
            )

            end = min(
                len(sentence_tokens),
                aspect_index + 5
            )

            context = " ".join(
                sentence_tokens[start:end]
            )

     
        # FINAL CLEANING
      

        context = (
            context
            .replace("\\n", " ")
            .strip("'\" ")
        )

       
        # SENTIMENT PREDICTION
       

        sentiment, confidence = (
            predict_sentiment(
                context
            )
        )

      
        
       
        seen.add(aspect)
        aspect_sentiments.append({

            "aspect": aspect,

            "sentence": sentence,

            "context": context,

            "sentiment": sentiment,

            "confidence": confidence
        })

    return aspect_sentiments


# GENERATE PDF REPORT


def generate_pdf_report(

    query,
    filtered_results
):

    buffer = BytesIO()

    doc = SimpleDocTemplate(

    buffer,

    rightMargin=40,
    leftMargin=40,

    topMargin=40,
    bottomMargin=40
    )

    styles = getSampleStyleSheet()

    elements = []

   
    # TITLE
   

    elements.append(

        Paragraph(

            "Semantic Search Report",

            styles['Title']
        )
    )

    elements.append(
        Spacer(1, 14)
    )

    
    # QUERY
   

    elements.append(

        Paragraph(

            f"<b>Search Query:</b> {query}",

            styles['BodyText']
        )
    )

    elements.append(
        Spacer(1, 14)
    )

    
    # RESULTS
   

    for idx, result in enumerate(

        filtered_results,
        start=1
    ):

        review = result['review']

        similarity = result['similarity']

        sentiment = result[
            'sentiment'
        ]

        confidence = result[
            'confidence'
        ]

        aspects = result[
            'aspects'
        ]

        elements.append(

            Paragraph(

                f"<b>Review {idx}</b>",

                styles['Heading2']
            )
        )

        elements.append(
            Spacer(1, 8)
        )

        elements.append(

            Paragraph(

                f"<b>Relevance Score:</b> "
                f"{similarity:.2f}",

                styles['BodyText']
            )
        )

        elements.append(

            Paragraph(

                f"<b>Overall Sentiment:</b> "
                f"{sentiment}",

                styles['BodyText']
            )
        )

        elements.append(

            Paragraph(

                f"<b>Confidence:</b> "
                f"{confidence:.2f}",

                styles['BodyText']
            )
        )

        elements.append(
            Spacer(1, 8)
        )

        elements.append(

            Paragraph(

                f"<b>Review:</b> "
                f"{review}",

                styles['BodyText']
            )
        )

        elements.append(
            Spacer(1, 10)
        )

        
        # ASPECT DETAILS
     

        elements.append(

            Paragraph(

                "<b>Aspect-Level Sentiment</b>",

                styles['Heading3']
            )
        )

        elements.append(
            Spacer(1, 6)
        )

        for item in aspects:

            elements.append(

                Paragraph(

                    f"<b>Aspect:</b> "
                    f"{item['aspect']}",

                    styles['BodyText']
                )
            )

            elements.append(

                Paragraph(

                    f"<b>Sentence:</b> "
                    f"{item['sentence']}",

                    styles['BodyText']
                )
            )

            elements.append(

                Paragraph(

                    f"<b>Context:</b> "
                    f"{item['context']}",

                    styles['BodyText']
                )
            )

            elements.append(

                Paragraph(

                    f"<b>Sentiment:</b> "
                    f"{item['sentiment']}",

                    styles['BodyText']
                )
            )

            elements.append(

                Paragraph(

                    f"<b>Confidence:</b> "
                    f"{item['confidence']:.2f}",

                    styles['BodyText']
                )
            )

            elements.append(
                Spacer(1, 10)
            )

        elements.append(
            Spacer(1, 18)
        )

    
    # BUILD PDF
    

    doc.build(elements)

    buffer.seek(0)

    return buffer

# TITLE

st.title(
    "Amazon NLP Retrieval System"
)

st.write(
    """
    Advanced Aspect-Based Sentiment Analysis    
    """
)


# SIDEBAR SETTINGS


st.sidebar.header(
    "Search Settings"
)

top_k = st.sidebar.slider(
    "Number of Reviews to Show",
    1,
    20,
    10
)

min_similarity = st.sidebar.slider(
    "Search Relevance",
    0.0,
    1.0,
    0.4
)

sentiment_filter = st.sidebar.selectbox(
    "Review Type",
    [
        "all",
        "positive",
        "neutral",
        "negative"
    ]
)


# FILE UPLOAD


uploaded_file = st.file_uploader(
    "Upload Review Dataset",
    type=["xlsx", "csv"]
)

if uploaded_file is not None:

   
    # LOAD DATA
    

    if uploaded_file.name.endswith(".xlsx"):

        df = pd.read_excel(
            uploaded_file
        )

    elif uploaded_file.name.endswith(".csv"):

        df = pd.read_csv(
            uploaded_file
        )

    else:

        st.error(
            "Unsupported file format."
        )

        st.stop()

    st.success(
        "Dataset uploaded successfully!"
    )

    st.write(
        f"Total Reviews: {len(df)}"
    )


    # PREVIEW
 

    st.subheader(
        "Dataset Preview"
    )

    st.dataframe(
        df.head()
    )

 
    # COLUMN SELECTION
 

    st.subheader(
        "Select Dataset Columns"
    )

    text_column = st.selectbox(
        "Select Review Text Column",
        df.columns
    )

    rating_column = st.selectbox(
        "Select Rating Column (Optional)",
        ["None"] + list(df.columns)
    )
    
    # SAVE DATASET
    

    temp_path = (
        f"temp_{uploaded_file.name}"
    )

    df.to_excel(
        temp_path,
        index=False
    )

  
    # USER QUERY
    query = st.text_input(
        "Enter your search query"
    )
 
    # BUILD SEARCH ENGINE
    if query:

        with st.spinner(
            "Building semantic index..."
        ):

            search_engine = load_search_engine(

                temp_path,

                text_column
            )

        st.success(
            "Semantic index ready!"
        )   
  
    # SEARCH
    if query:

       
        # EXTRACT ASPECTS
     

        st.subheader(
            "Extracted Aspects"
        )

        aspects = extract_aspects(
            query
        )

        if aspects:

            st.write(aspects)

        else:

            st.write(
                "No aspects detected."
            )

      
        # SEARCH RESULTS
       

        st.subheader(
            "Semantic Search Results"
        )

        results = search_engine.search(
            query,
            top_k=top_k*3
        )

     
        # METRICS
      

        col1, col2, col3 = st.columns(3)

        col1.metric(
            "Retrieved Reviews",
            len(results)
        )

        col2.metric(
            "Detected Aspects",
            len(aspects)
        )

        if len(results) > 0:

            avg_similarity = round(

                sum(
                    [
                        r['similarity']
                        for r in results
                    ]
                ) / len(results),

                2
            )

        else:

            avg_similarity = 0

        col3.metric(
            "Average Relevance",
            avg_similarity
        )

        
        # MATCH QUALITY
      

        retrieved_reviews = [
            r['review']
            for r in results
        ]

        relevant_reviews = []

        for review in retrieved_reviews:

            review_lower = review.lower()

            for aspect in aspects:

               
                # SPLIT ASPECT PHRASE
           

                aspect_words = aspect.split()

                # COUNT MATCHES
               

                matches = sum(

                    1

                    for word in aspect_words

                    if word in review_lower
                )

             
                # FLEXIBLE MATCHING
             

                if matches >= max(
                    1,
                    len(aspect_words) // 2
                ):

                    relevant_reviews.append(
                        review
                    )

                    break

        precision = precision_at_k(
            relevant_reviews,
            retrieved_reviews,
            min(5, len(retrieved_reviews))
        )

        st.metric(
            "Match Quality",
            round(precision, 2)
        )

        sentiments = []
        filtered_results = []

        result_count = 0

      
        # DISPLAY RESULTS
      
        reviews_to_parse = [

            result['review']

            for result in results
        ]

        parsed_docs = list(

            nlp.pipe(

                reviews_to_parse,

                batch_size=64
            )
        )

        for result, parsed_doc in zip(

            results,
            parsed_docs
        ):

            review = result['review']

            similarity = result['similarity']

           
            # SIMILARITY FILTER
           

            dynamic_threshold = max(
                min_similarity,
                avg_similarity - 0.10
            )

            if similarity < dynamic_threshold:
                continue

            formatted_review = (

                review
                .replace("\\n", "\n")
                .strip("'\" ")
            )

          
            # OVERALL SENTIMENT
        

            review_sentiment, confidence = (
                predict_sentiment(
                    review
                )
            )

           
            # SENTIMENT FILTER
           

            if (
                sentiment_filter != "all"
                and review_sentiment != sentiment_filter
            ):
                continue

            sentiments.append(
                review_sentiment
            )

            result_count += 1

            
            # ASPECT ANALYSIS
           

            

            aspect_results = (
                aspect_sentiment_analysis(
                    parsed_doc
                )
            )
            filtered_results.append({

                "review": formatted_review,

                "similarity": similarity,

                "sentiment": review_sentiment,

                "confidence": confidence,

                "aspects": aspect_results
            })

          
            # REVIEW CARD
         

            with st.expander(
                f"Review Match • Score {similarity:.2f}"
            ):

                st.markdown(
                    "### Review"
                )

                st.markdown(
                    formatted_review
                )

                st.write(
                    f"Relevance Score: {similarity:.2f}"
                )

                st.progress(
                    min(
                        float(similarity),
                        1.0
                    )
                )

               
                # OVERALL SENTIMENT
               

                st.markdown(
                    "### Overall Review Sentiment"
                )

                st.write(
                    f"Confidence: {confidence:.2f}"
                )

                if review_sentiment == "positive":

                    st.success(
                        "Positive"
                    )

                elif review_sentiment == "neutral":

                    st.warning(
                        "Neutral"
                    )

                else:

                    st.error(
                        "Negative"
                    )

                
                # ASPECT SENTIMENTS
               

                st.markdown(
                    "### Aspect-Level Sentiment"
                )

                for item in aspect_results:

                    aspect = item['aspect']

                    sentiment = item['sentiment']

                    sentence = (
                        item['sentence']
                        .replace("\\n", " ")
                        .strip("'\" ")
                    )

                    context = (
                        item['context']
                        .replace("\\n", " ")
                        .strip("'\" ")
                    )

                    confidence = item[
                        'confidence'
                    ]

                    st.write(
                        f"Aspect: {aspect}"
                    )

                    st.caption(
                        f"Sentence: {sentence}"
                    )

                    st.caption(
                        f"Context: {context}"
                    )

                    st.caption(
                        f"Confidence: {confidence:.2f}"
                    )

                    if sentiment == "positive":

                        st.success(
                            f"Sentiment: {sentiment}"
                        )

                    elif sentiment == "neutral":

                        st.warning(
                            f"Sentiment: {sentiment}"
                        )

                    else:

                        st.error(
                            f"Sentiment: {sentiment}"
                        )

                    st.write("---")

        
        # NO RESULTS
        

        if result_count == 0:

            st.warning(
                """
                No matching reviews found
                with current filters.
                """
            )

    
        # SENTIMENT DASHBOARD
      
        
        
        

        if sentiments:

            st.subheader(
                "Sentiment Distribution"
            )

            sentiment_df = pd.DataFrame({

                'Sentiment': sentiments

            })

            fig = px.pie(

                sentiment_df,

                names='Sentiment',

                title='Sentiment Distribution'
            )

            st.plotly_chart(

                fig,

                use_container_width=True
            )

           
            # PDF DOWNLOAD
            

            if filtered_results:

                pdf_buffer = generate_pdf_report(

                    query,
                    filtered_results
                )

                st.download_button(

                    label="Download PDF Report",

                    data=pdf_buffer,

                    file_name="semantic_search_report.pdf",

                    mime="application/pdf"
                )