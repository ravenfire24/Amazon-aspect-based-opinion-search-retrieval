# Amazon Review Intelligence

**Live Demo:** [https://amazon-aspect-based-opinion-search.vercel.app](https://amazon-aspect-based-opinion-search.vercel.app)

Amazon Review Intelligence is a web-based opinion search and review analysis
system for Amazon product reviews. The project is built to help auditors,
analysts, and product teams quickly understand what customers are saying about
specific product issues such as battery life, screen quality, charger problems,
software usability, build quality, price, and support.

Instead of forcing a reviewer to manually read long customer reviews, the system
returns ranked review results, highlights relevant aspect evidence, and presents
plain-language summaries such as what the customer is talking about, the
sentiment direction, product ID, rating, review date, and purchase status.

![alt text](https://github.com/ravenfire24/Amazon-aspect-based-opinion-search-retrieval/blob/main/Capture.PNG)

## Purpose

The goal of this project is to demonstrate a production-oriented review
intelligence workflow:

- Load a structured Amazon review dataset.
- Store the reviews in a cloud MySQL database.
- Retrieve semantically relevant reviews for a user query.
- Extract product-aspect evidence from review text.
- Present the results in a clear dashboard that an auditor can understand.

The application focuses on explainable results. Each search result includes the
original review text and the supporting evidence sentence so the reviewer can
see why a result was returned.

## Main Features

- Search Amazon reviews by issue or product topic.
- Display ranked review results with search scores.
- Show customer-facing metadata clearly:
  - Product ID
  - Customer rating
  - Review date
  - Verified purchase status
- Summarize what the customer is talking about.
- Show aspect evidence cards with sentiment labels and confidence scores.
- Keep full reviews available while showing shorter excerpts by default.
- Track query and result activity in the database for traceability.

## Example Queries

Users can search with short product-issue phrases. Good example queries include:

- `battery issues`
- `screen quality`
- `charger problem`
- `software problems`
- `easy to use`
- `build quality`
- `price and value`
- `customer support`

## Components Used

### Frontend

- **Next.js App Router** for the web application structure.
- **React client components** for interactive search, result rendering, and
  expandable review text.
- **CSS** for the auditor-friendly dashboard layout and responsive UI.

### Backend/API

- **Next.js Route Handlers** for API endpoints.
- `/api/search` for review retrieval.
- `/api/health` for database and deployment health checks.

### Database

- **MySQL** as the cloud database.
- `review_intelligence` schema for production review data.
- MySQL full-text indexes for review title and review body candidate search.

### Data Processing

- **Python** scripts for local data preparation.
- **openpyxl** for streaming Excel review data.
- **PyMySQL** for loading processed rows into MySQL.
- Shared text normalization, synonym expansion, and cosine-style reranking for
  semantic retrieval without requiring exact keyword matches.
- A lightweight lexicon-based aspect extraction script for identifying product
  topics and sentiment evidence.

### Deployment

- **Vercel** for hosting the Next.js application.
- Environment variables are used for database connection settings and SSL
  configuration.

## System Flow

```text
dataset.xlsx
  -> Python import script
  -> MySQL review_intelligence database
  -> aspect evidence extraction
  -> Next.js API routes
  -> Review Intelligence dashboard
  -> Vercel deployment
```

## Database Design

The project uses the following main tables:

- `datasets`: tracks imported review datasets.
- `reviews`: stores individual Amazon review records.
- `aspects`: stores normalized product aspects.
- `review_aspects`: stores evidence sentences and sentiment labels.
- `search_queries`: logs submitted search queries.
- `search_results`: stores ranked results for traceability.
- `reports`: reserved for future report-generation workflows.
- `schema_migrations`: tracks database schema setup.

The app searches only completed datasets marked as `indexed`, which prevents
failed or partial imports from appearing in the dashboard.

## Dataset Scope

The Excel workbook contains the Amazon review data. The deployed database uses
a sample of **50,000 reviews** for the live application.


## Security and Secrets

Sensitive credentials are not stored in the repository. Database passwords,
connection URLs, SSL certificates, and local data files are handled through
local files or Vercel environment variables.

The repository ignores:

```text
.env
.env.*
*.pem
*.key
*.crt
*.cert
```

This prevents accidental commits of database credentials, SSL certificates, and
the review dataset.

## Project Summary

Amazon Review Intelligence demonstrates an end-to-end review analytics workflow:
data ingestion, database storage, search retrieval, aspect evidence extraction,
auditor-friendly UI design, and cloud deployment. It is designed to make large
sets of product reviews easier to inspect, explain, and validate.
