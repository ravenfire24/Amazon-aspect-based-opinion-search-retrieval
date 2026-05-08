import pandas as pd
import joblib

from sklearn.model_selection import train_test_split

from sklearn.feature_extraction.text import (
    TfidfVectorizer
)

from sklearn.linear_model import (
    LogisticRegression
)

from sklearn.metrics import (
    classification_report
)

from preprocessing import (
    clean_text,
    label_sentiment
)


# LOAD DATASET


def load_dataset(filepath):

    if filepath.endswith(".xlsx"):

        return pd.read_excel(filepath)

    elif filepath.endswith(".csv"):

        return pd.read_csv(filepath)

    else:

        raise ValueError(
            "Unsupported file format"
        )


# USER INPUTS


filepath = input(
    "Enter dataset path: "
)

df = load_dataset(filepath)


# SHOW AVAILABLE COLUMNS


print("\nAvailable Columns:")
print(df.columns.tolist())


# COLUMN SELECTION


text_column = input(
    "\nEnter review text column name: "
)

rating_column = input(
    "Enter rating column name: "
)

# -----------------------------------
# VALIDATION
# -----------------------------------

if text_column not in df.columns:

    raise ValueError(
        f"Column '{text_column}' not found."
    )

if rating_column not in df.columns:

    raise ValueError(
        f"Column '{rating_column}' not found."
    )


# KEEP REQUIRED COLUMNS


df = df[
    [text_column, rating_column]
]

print(
    f"\nDataset Size: {len(df)}"
)


# REMOVE MISSING VALUES


df.dropna(inplace=True)


# SAMPLE SIZE


sample_size = int(
    input(
        "\nEnter sample size: "
    )
)

sample_size = min(
    sample_size,
    len(df)
)

df = df.sample(
    sample_size,
    random_state=42
)


# CLEAN TEXT


df['clean_review'] = df[
    text_column
].apply(clean_text)


# LABELS


df['sentiment'] = df[
    rating_column
].apply(label_sentiment)


# FEATURES / LABELS


X = df['clean_review']

y = df['sentiment']


# TF-IDF SETTINGS


max_features = int(
    input(
        "\nEnter TF-IDF max features: "
    )
)


# TF-IDF VECTORIZATION


vectorizer = TfidfVectorizer(
    max_features=max_features
)

X_vectorized = vectorizer.fit_transform(
    X
)


# TRAIN TEST SPLIT


X_train, X_test, y_train, y_test = (
    train_test_split(

        X_vectorized,

        y,

        test_size=0.2,

        random_state=42,

        stratify=y
    )
)


# MODEL SETTINGS


max_iter = int(
    input(
        "\nEnter Logistic Regression max iterations: "
    )
)


# MODEL


model = LogisticRegression(
    max_iter=max_iter
)


# TRAIN MODEL


model.fit(
    X_train,
    y_train
)


# PREDICT


predictions = model.predict(
    X_test
)

# -----------------------------------
# METRICS
# -----------------------------------

print(
    "\nClassification Report:\n"
)

print(
    classification_report(

        y_test,

        predictions,

        zero_division=0
    )
)


# SAVE PATHS


model_save_path = input(
    "\nEnter model save path "
    "(default: models/logistic_model.pkl): "
)

if not model_save_path.strip():

    model_save_path = (
        "models/logistic_model.pkl"
    )

vectorizer_save_path = input(
    "\nEnter vectorizer save path "
    "(default: models/vectorizer.pkl): "
)

if not vectorizer_save_path.strip():

    vectorizer_save_path = (
        "models/vectorizer.pkl"
    )


# SAVE MODEL


joblib.dump(
    model,
    model_save_path
)


# SAVE VECTORIZER


joblib.dump(
    vectorizer,
    vectorizer_save_path
)

print(
    "\nTraining complete."
)

print(
    f"\nModel saved to: "
    f"{model_save_path}"
)

print(
    f"Vectorizer saved to: "
    f"{vectorizer_save_path}"
)