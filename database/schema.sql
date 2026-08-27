CREATE TABLE IF NOT EXISTS schema_migrations (
    version VARCHAR(64) PRIMARY KEY,
    applied_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS datasets (
    id CHAR(36) PRIMARY KEY,
    source_filename VARCHAR(255) NOT NULL,
    text_column VARCHAR(128) NOT NULL,
    rating_column VARCHAR(128) NULL,
    row_count INT UNSIGNED NOT NULL DEFAULT 0,
    status ENUM('uploaded', 'indexed', 'failed') NOT NULL DEFAULT 'uploaded',
    error_message TEXT NULL,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    INDEX idx_datasets_status_created (status, created_at)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS reviews (
    id BIGINT UNSIGNED PRIMARY KEY AUTO_INCREMENT,
    dataset_id CHAR(36) NOT NULL,
    source_row INT UNSIGNED NOT NULL,
    review_id VARCHAR(128) NULL,
    product_id VARCHAR(128) NULL,
    customer_id VARCHAR(128) NULL,
    review_title TEXT NULL,
    review_text LONGTEXT NOT NULL,
    review_written_date DATE NULL,
    customer_name VARCHAR(255) NULL,
    review_from_title TEXT NULL,
    helpful_count INT UNSIGNED NULL,
    out_of_helpful_count INT UNSIGNED NULL,
    customer_review_rating TINYINT UNSIGNED NULL,
    number_of_comments INT UNSIGNED NULL,
    amazon_verified_purchase BOOLEAN NULL,
    amazon_vine_program_review BOOLEAN NULL,
    raw_metadata JSON NULL,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT fk_reviews_dataset
        FOREIGN KEY (dataset_id) REFERENCES datasets(id)
        ON DELETE CASCADE,
    UNIQUE KEY uq_reviews_dataset_row (dataset_id, source_row),
    INDEX idx_reviews_dataset (dataset_id),
    INDEX idx_reviews_product (product_id),
    INDEX idx_reviews_rating (customer_review_rating),
    INDEX idx_reviews_written_date (review_written_date),
    FULLTEXT KEY ft_reviews_text (review_title, review_text)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS aspects (
    id BIGINT UNSIGNED PRIMARY KEY AUTO_INCREMENT,
    name VARCHAR(160) NOT NULL,
    normalized_name VARCHAR(160) NOT NULL,
    category VARCHAR(120) NULL,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    UNIQUE KEY uq_aspects_normalized_name (normalized_name),
    INDEX idx_aspects_category (category)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS review_aspects (
    id BIGINT UNSIGNED PRIMARY KEY AUTO_INCREMENT,
    review_id BIGINT UNSIGNED NOT NULL,
    aspect_id BIGINT UNSIGNED NOT NULL,
    sentence TEXT NOT NULL,
    context TEXT NOT NULL,
    sentiment ENUM('negative', 'neutral', 'positive') NOT NULL,
    confidence DECIMAL(5,4) NOT NULL,
    extractor_version VARCHAR(80) NOT NULL,
    sentiment_model_version VARCHAR(160) NOT NULL,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT fk_review_aspects_review
        FOREIGN KEY (review_id) REFERENCES reviews(id)
        ON DELETE CASCADE,
    CONSTRAINT fk_review_aspects_aspect
        FOREIGN KEY (aspect_id) REFERENCES aspects(id)
        ON DELETE CASCADE,
    INDEX idx_review_aspects_review (review_id),
    INDEX idx_review_aspects_aspect_sentiment (aspect_id, sentiment),
    INDEX idx_review_aspects_sentiment_confidence (sentiment, confidence)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS search_queries (
    id BIGINT UNSIGNED PRIMARY KEY AUTO_INCREMENT,
    query_text TEXT NOT NULL,
    normalized_query VARCHAR(512) NOT NULL,
    filters JSON NULL,
    result_count INT UNSIGNED NOT NULL DEFAULT 0,
    latency_ms INT UNSIGNED NULL,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    INDEX idx_search_queries_created (created_at),
    INDEX idx_search_queries_normalized (normalized_query)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS search_results (
    id BIGINT UNSIGNED PRIMARY KEY AUTO_INCREMENT,
    query_id BIGINT UNSIGNED NOT NULL,
    review_id BIGINT UNSIGNED NOT NULL,
    result_rank INT UNSIGNED NOT NULL,
    similarity DECIMAL(6,5) NOT NULL,
    overall_sentiment ENUM('negative', 'neutral', 'positive') NULL,
    overall_confidence DECIMAL(5,4) NULL,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT fk_search_results_query
        FOREIGN KEY (query_id) REFERENCES search_queries(id)
        ON DELETE CASCADE,
    CONSTRAINT fk_search_results_review
        FOREIGN KEY (review_id) REFERENCES reviews(id)
        ON DELETE CASCADE,
    UNIQUE KEY uq_search_results_query_rank (query_id, result_rank),
    INDEX idx_search_results_query (query_id),
    INDEX idx_search_results_review (review_id),
    INDEX idx_search_results_similarity (similarity)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS reports (
    id BIGINT UNSIGNED PRIMARY KEY AUTO_INCREMENT,
    query_id BIGINT UNSIGNED NOT NULL,
    report_format ENUM('pdf', 'json') NOT NULL DEFAULT 'pdf',
    storage_url TEXT NULL,
    status ENUM('queued', 'ready', 'failed') NOT NULL DEFAULT 'queued',
    error_message TEXT NULL,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    completed_at TIMESTAMP NULL,
    CONSTRAINT fk_reports_query
        FOREIGN KEY (query_id) REFERENCES search_queries(id)
        ON DELETE CASCADE,
    INDEX idx_reports_query (query_id),
    INDEX idx_reports_status_created (status, created_at)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

INSERT IGNORE INTO schema_migrations (version)
VALUES ('001_initial_review_intelligence_schema');
