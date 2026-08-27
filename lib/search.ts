import { getPool } from "./db";
import type { ResultSetHeader, RowDataPacket } from "mysql2";
import {
  buildSemanticVector,
  cosineSimilarity,
  expandSearchTerms,
  inferSemanticProfiles,
  normalizeText,
} from "./text-processing";

export type AspectSentiment = {
  aspect: string;
  category: string | null;
  sentence: string;
  sentiment: "negative" | "neutral" | "positive";
  confidence: number;
};

export type ReviewSearchResult = {
  id: number;
  productId: string | null;
  title: string | null;
  text: string;
  rating: number | null;
  writtenDate: string | null;
  verifiedPurchase: boolean | null;
  relevance: number;
  aspects: AspectSentiment[];
};

interface ReviewRow extends RowDataPacket {
  id: number;
  product_id: string | null;
  review_title: string | null;
  review_text: string;
  customer_review_rating: number | null;
  review_written_date: Date | string | null;
  amazon_verified_purchase: number | boolean | null;
  lexical_relevance: number;
}

interface AspectRow extends RowDataPacket {
  review_id: number;
  aspect: string;
  category: string | null;
  sentence: string;
  sentiment: "negative" | "neutral" | "positive";
  confidence: string | number;
}

function normalizeQuery(query: string) {
  return normalizeText(query);
}

function toDateString(value: Date | string | null) {
  if (!value) {
    return null;
  }

  if (value instanceof Date) {
    return value.toISOString().slice(0, 10);
  }

  return value;
}

function toReadableText(value: string | null) {
  if (!value) {
    return "";
  }

  return value
    .replace(/\\r\\n|\\n|\\r/g, "\n")
    .replace(/\r\n|\r/g, "\n")
    .replace(/\n{3,}/g, "\n\n")
    .trim();
}

export async function searchReviews(query: string, limit: number) {
  const normalizedQuery = normalizeQuery(query);

  if (!normalizedQuery) {
    return [];
  }

  const safeLimit = Math.min(Math.max(limit, 1), 25);
  const candidateLimit = Math.min(Math.max(safeLimit * 20, 75), 300);
  const pool = getPool();
  const startedAt = Date.now();
  const expandedTerms = expandSearchTerms(normalizedQuery);
  const expandedQuery = expandedTerms.join(" ");
  const inferredAspects = inferSemanticProfiles(normalizedQuery);
  const queryVector = buildSemanticVector(
    [normalizedQuery, expandedTerms.join(" "), inferredAspects.join(" ")].join(" ")
  );

  const candidateRows = new Map<number, ReviewRow>();

  if (expandedQuery) {
    const [fullTextRows] = await pool.query<ReviewRow[]>(
      `
        SELECT
          r.id,
          r.product_id,
          r.review_title,
          r.review_text,
          r.customer_review_rating,
          r.review_written_date,
          r.amazon_verified_purchase,
          MATCH(r.review_title, r.review_text)
            AGAINST (:query IN NATURAL LANGUAGE MODE) AS lexical_relevance
        FROM reviews r
        INNER JOIN datasets d ON d.id = r.dataset_id
        WHERE d.status = 'indexed'
          AND MATCH(r.review_title, r.review_text)
          AGAINST (:query IN NATURAL LANGUAGE MODE)
        ORDER BY lexical_relevance DESC, r.id DESC
        LIMIT ${candidateLimit}
      `,
      {
        query: expandedQuery,
      }
    );

    for (const row of Array.isArray(fullTextRows) ? fullTextRows : []) {
      candidateRows.set(row.id, row);
    }
  }

  if (inferredAspects.length > 0) {
    const placeholders = inferredAspects.map(() => "?").join(",");
    const [aspectCandidateRows] = await pool.query<ReviewRow[]>(
      `
        SELECT
          r.id,
          r.product_id,
          r.review_title,
          r.review_text,
          r.customer_review_rating,
          r.review_written_date,
          r.amazon_verified_purchase,
          aspect_hits.lexical_relevance
        FROM reviews r
        INNER JOIN datasets d ON d.id = r.dataset_id
        INNER JOIN (
          SELECT
            ra.review_id,
            MAX(ra.confidence) AS lexical_relevance
          FROM review_aspects ra
          INNER JOIN aspects a ON a.id = ra.aspect_id
          WHERE a.normalized_name IN (${placeholders})
          GROUP BY ra.review_id
        ) aspect_hits ON aspect_hits.review_id = r.id
        WHERE d.status = 'indexed'
        ORDER BY lexical_relevance DESC, r.id DESC
        LIMIT ${candidateLimit}
      `,
      inferredAspects
    );

    for (const row of Array.isArray(aspectCandidateRows) ? aspectCandidateRows : []) {
      const existing = candidateRows.get(row.id);

      if (!existing || Number(row.lexical_relevance) > Number(existing.lexical_relevance)) {
        candidateRows.set(row.id, row);
      }
    }
  }

  const rows = Array.from(candidateRows.values())
    .map((row) => {
      const documentVector = buildSemanticVector(
        `${row.review_title ?? ""} ${row.review_text}`
      );
      const semanticScore = cosineSimilarity(queryVector, documentVector);
      const lexicalScore = Math.min(Math.max(Number(row.lexical_relevance) || 0, 0), 1);
      const aspectBoost =
        inferredAspects.length > 0 && semanticScore > 0 ? 0.08 : 0;
      const relevance = Math.min(
        1,
        0.72 * semanticScore + 0.28 * lexicalScore + aspectBoost
      );

      return {
        ...row,
        relevance,
      };
    })
    .filter((row) => row.relevance > 0)
    .sort((left, right) => right.relevance - left.relevance || right.id - left.id)
    .slice(0, safeLimit);
  const reviewIds = rows.map((row) => row.id);
  const aspectsByReviewId = new Map<number, AspectSentiment[]>();

  if (reviewIds.length > 0) {
    const placeholders = reviewIds.map(() => "?").join(",");
    const [aspectRows] = await pool.query<AspectRow[]>(
      `
        SELECT
          ra.review_id,
          a.name AS aspect,
          a.category,
          ra.sentence,
          ra.sentiment,
          ra.confidence
        FROM review_aspects ra
        INNER JOIN aspects a ON a.id = ra.aspect_id
        WHERE ra.review_id IN (${placeholders})
        ORDER BY ra.confidence DESC
      `,
      reviewIds
    );

    for (const row of Array.isArray(aspectRows) ? aspectRows : []) {
      const existing = aspectsByReviewId.get(row.review_id) ?? [];
      existing.push({
        aspect: row.aspect,
        category: row.category,
        sentence: toReadableText(row.sentence),
        sentiment: row.sentiment,
        confidence: Number(row.confidence),
      });
      aspectsByReviewId.set(row.review_id, existing);
    }
  }

  const results = rows.map((row) => ({
    id: row.id,
    productId: row.product_id,
    title: toReadableText(row.review_title),
    text: toReadableText(row.review_text),
    rating: row.customer_review_rating,
    writtenDate: toDateString(row.review_written_date),
    verifiedPurchase:
      row.amazon_verified_purchase === null
        ? null
        : Boolean(row.amazon_verified_purchase),
    relevance: Number(row.relevance),
    aspects: aspectsByReviewId.get(row.id) ?? [],
  }));

  try {
    const [queryResult] = await pool.query<ResultSetHeader>(
      `
        INSERT INTO search_queries
          (query_text, normalized_query, result_count, latency_ms)
        VALUES
          (:queryText, :normalizedQuery, :resultCount, :latencyMs)
      `,
      {
        queryText: query,
        normalizedQuery,
        resultCount: results.length,
        latencyMs: Date.now() - startedAt,
      }
    );

    const queryId = Number(queryResult.insertId);

    if (queryId && results.length > 0) {
      await pool.query(
        `
          INSERT INTO search_results
            (query_id, review_id, result_rank, similarity)
          VALUES ?
        `,
        [
          results.map((result, index) => [
            queryId,
            result.id,
            index + 1,
            Math.max(0, Math.min(Number(result.relevance), 1)),
          ]),
        ]
      );
    }
  } catch (error) {
    console.warn("Search analytics logging failed.", error);
  }

  return results;
}
