import pandas as pd

from datasets import Dataset

from transformers import (
    AutoTokenizer,
    AutoModelForSequenceClassification,
    Trainer,
    TrainingArguments
)

from sklearn.model_selection import train_test_split

from preprocessing import label_sentiment


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


# VALIDATION


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


# REMOVE MISSING VALUES


df.dropna(inplace=True)

print(
    f"\nDataset Size: {len(df)}"
)


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


# LABELS


df['label'] = df[
    rating_column
].apply(label_sentiment)


# TRAIN / TEST SPLIT


train_df, test_df = train_test_split(
    df,
    test_size=0.2,
    random_state=42
)


# HF DATASETS


train_dataset = Dataset.from_pandas(
    train_df
)

test_dataset = Dataset.from_pandas(
    test_df
)


# MODEL NAME


MODEL_NAME = input(
    "\nEnter transformer model name "
    "(default: bert-base-uncased): "
)

if not MODEL_NAME.strip():

    MODEL_NAME = "bert-base-uncased"


# TOKENIZER


tokenizer = AutoTokenizer.from_pretrained(
    MODEL_NAME
)


# TOKENIZATION


def tokenize(batch):

    return tokenizer(

        batch[text_column],

        padding='max_length',

        truncation=True,

        max_length=128
    )

train_dataset = train_dataset.map(
    tokenize,
    batched=True
)

test_dataset = test_dataset.map(
    tokenize,
    batched=True
)


# DATA FORMAT


train_dataset.set_format(
    type='torch',
    columns=[
        'input_ids',
        'attention_mask',
        'label'
    ]
)

test_dataset.set_format(
    type='torch',
    columns=[
        'input_ids',
        'attention_mask',
        'label'
    ]
)


# MODEL


model = AutoModelForSequenceClassification.from_pretrained(
    MODEL_NAME,
    num_labels=3
)

# TRAINING SETTINGS


epochs = int(
    input(
        "\nEnter number of epochs: "
    )
)

batch_size = int(
    input(
        "Enter batch size: "
    )
)

learning_rate = float(
    input(
        "Enter learning rate "
        "(example: 2e-5): "
    )
)


# TRAINING ARGUMENTS


training_args = TrainingArguments(

    output_dir='./bert_results',

    learning_rate=learning_rate,

    per_device_train_batch_size=batch_size,

    num_train_epochs=epochs,

    logging_dir='./logs'
)


# TRAINER


trainer = Trainer(

    model=model,

    args=training_args,

    train_dataset=train_dataset,

    eval_dataset=test_dataset
)


# TRAIN


trainer.train()


# SAVE MODEL


save_path = input(
    "\nEnter model save path "
    "(default: models/bert_sentiment): "
)

if not save_path.strip():

    save_path = "models/bert_sentiment"

model.save_pretrained(
    save_path
)

tokenizer.save_pretrained(
    save_path
)

print(
    "\nBERT training complete."
)

print(
    f"\nModel saved to: {save_path}"
)