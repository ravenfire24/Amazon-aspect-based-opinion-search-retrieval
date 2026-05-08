import faiss
import pandas as pd
import numpy as np
import os
import pickle

from sentence_transformers import SentenceTransformer


class SemanticSearch:

    def __init__(self):

       
        # LOAD EMBEDDING MODEL
   

        self.model = SentenceTransformer(
            'all-MiniLM-L6-v2'
        )

        self.index = None

        self.reviews = []

   
    # BUILD FAISS INDEX
   

    def build_index(
        self,
        filepath,
        text_column
    ):

        dataset_name = (

            os.path.basename(filepath)
            .split(".")[0]
        )

        index_path = (
            f"{dataset_name}_faiss.bin"
        )

        reviews_path = (
            f"{dataset_name}_reviews.pkl"
        )

       
        # LOAD SAVED INDEX
       

        if (

            os.path.exists(index_path)

            and os.path.exists(reviews_path)
        ):

            self.index = faiss.read_index(
                index_path
            )

            with open(
                reviews_path,
                "rb"
            ) as f:

                self.reviews = pickle.load(f)

            return

       
        # LOAD DATASET
        

        if filepath.endswith(".xlsx"):

            df = pd.read_excel(filepath)

        elif filepath.endswith(".csv"):

            df = pd.read_csv(filepath)

        else:

            raise ValueError(
                "Unsupported file format"
            )

     
        # VALIDATION
      

        if text_column not in df.columns:

            raise ValueError(
                f"Dataset must contain '{text_column}' column"
            )

       
        # REMOVE MISSING VALUES
        

        df.dropna(
            subset=[text_column],
            inplace=True
        )

     
        # STORE REVIEWS
        

        self.reviews = df[
            text_column
        ].astype(str).tolist()

        
        # CREATE EMBEDDINGS
        

        embeddings = self.model.encode(

            self.reviews,

            batch_size=256,

            show_progress_bar=False,

            convert_to_numpy=True
        )

        
        # NORMALIZE EMBEDDINGS
       

        faiss.normalize_L2(
            embeddings
        )

      
        # BUILD INDEX
        

        dimension = embeddings.shape[1]

        self.index = faiss.IndexFlatIP(
            dimension
        )

        self.index.add(
            embeddings
        )

       
        # SAVE INDEX
        

        faiss.write_index(

            self.index,

            index_path
        )

        with open(
            reviews_path,
            "wb"
        ) as f:

            pickle.dump(
                self.reviews,
                f
            )

   
    # SEARCH
   

    def search(
        self,
        query,
        top_k=5
    ):

        
        # QUERY EMBEDDING
        

        query_embedding = self.model.encode(

            [query],

            batch_size=32,

            show_progress_bar=False,

            convert_to_numpy=True
        )

       
        # NORMALIZE QUERY
      

        faiss.normalize_L2(
            query_embedding
        )

      
        # SEARCH
      

        similarities, indices = self.index.search(

            query_embedding,

            top_k
        )

       
        # FORMAT RESULTS
      

        results = []

        for idx, similarity in zip(

            indices[0],

            similarities[0]
        ):

            results.append({

                'review': self.reviews[idx],

                'similarity': round(
                    float(similarity),
                    2
                )
            })

        return results