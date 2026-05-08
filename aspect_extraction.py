import spacy

from collections import Counter


# LOAD SPACY MODEL


nlp = spacy.load("en_core_web_sm")


# DYNAMIC ASPECT EXTRACTION


def extract_aspects(text):

    doc = nlp(text)

    candidate_aspects = []

   
    # EXTRACT NOUN PHRASES
   

    for chunk in doc.noun_chunks:

      
        # KEEP IMPORTANT NOUNS
      

        clean_tokens = [

            token.text.lower()

            for token in chunk

            if (

                token.pos_ in [
                    "NOUN",
                    "PROPN",
                    "ADJ"
                ]

                and not token.is_stop

                and not token.is_punct
            )
        ]

        aspect = " ".join(
            clean_tokens
        ).strip()

        if len(aspect) > 2:

            candidate_aspects.append(
                aspect
            )

    
    # FREQUENCY SCORING
   

    aspect_counts = Counter(
        candidate_aspects
    )

    aspects = [

        aspect

        for aspect, count in aspect_counts.items()

        if count >= 1
    ]

    return list(set(aspects))