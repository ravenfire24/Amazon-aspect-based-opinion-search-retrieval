"use client";

import { FormEvent, useMemo, useState } from "react";

type AspectSentiment = {
  aspect: string;
  category: string | null;
  sentence: string;
  sentiment: "negative" | "neutral" | "positive";
  confidence: number;
};

type ReviewResult = {
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

type SearchResponse = {
  query: string;
  count: number;
  results: ReviewResult[];
};

type EvidenceGroup = {
  topic: string;
  category: string;
  evidence: AspectSentiment[];
  signal: string;
  meaning: string;
  confidence: string;
};

const topicLabels: Record<string, string> = {
  "battery life": "Battery life / charging",
  charger: "Charger performance",
  connectivity: "Connectivity",
  performance: "Performance",
  screen: "Screen quality",
  software: "Software",
  "user interface": "User interface",
  "ease of use": "Ease of use",
  "sound quality": "Sound quality",
  "camera quality": "Camera quality",
  "build quality": "Build quality",
  "fit and comfort": "Fit and comfort",
  "price and value": "Price and value",
  "storage and memory": "Storage / memory",
  "customer support": "Customer support",
};

function uniqueValues(values: string[]) {
  return Array.from(new Set(values.filter(Boolean)));
}

function getTopicLabel(topic: string) {
  return topicLabels[topic] ?? topic;
}

function formatCategory(category: string) {
  const normalized = category.trim();

  if (!normalized) {
    return "Uncategorized";
  }

  return normalized.charAt(0).toUpperCase() + normalized.slice(1);
}

function toListText(values: string[]) {
  if (values.length <= 1) {
    return values[0] ?? "";
  }

  return `${values.slice(0, -1).join(", ")} and ${values[values.length - 1]}`;
}

function getUniqueEvidence(aspects: AspectSentiment[]) {
  const seen = new Set<string>();

  return aspects.filter((aspect) => {
    const key = `${aspect.aspect}-${aspect.sentence}`;

    if (seen.has(key)) {
      return false;
    }

    seen.add(key);
    return true;
  });
}

function isNoisyConnectivityEvidence(aspect: AspectSentiment) {
  const sentence = aspect.sentence.toLowerCase();

  return (
    aspect.aspect === "connectivity" &&
    /\b(charg|battery|batteries|lead|leads|charger)\b/.test(sentence) &&
    !/\b(wifi|wireless|bluetooth|usb|signal|pairing)\b/.test(sentence)
  );
}

function isNoisyCameraEvidence(aspect: AspectSentiment) {
  const sentence = aspect.sentence.toLowerCase();

  return (
    aspect.aspect === "camera quality" &&
    /\b(battery|batteries|power|charge|charging|charger)\b/.test(sentence) &&
    !/\b(camera quality|photo quality|picture quality|image quality|blurry|sharp|clear lens)\b/.test(sentence)
  );
}

function isWeakEvidence(aspect: AspectSentiment) {
  const words = aspect.sentence.trim().split(/\s+/);

  return (
    words.length < 7 &&
    aspect.sentiment === "neutral" &&
    aspect.confidence <= 0.55
  );
}

function getAuditorEvidence(aspects: AspectSentiment[]) {
  return getUniqueEvidence(aspects).filter(
    (aspect) =>
      !isNoisyConnectivityEvidence(aspect) && !isNoisyCameraEvidence(aspect)
  );
}

function getUsefulEvidence(aspects: AspectSentiment[]) {
  const evidence = getAuditorEvidence(aspects);
  const usefulEvidence = evidence.filter((aspect) => !isWeakEvidence(aspect));

  return usefulEvidence.length > 0 ? usefulEvidence : evidence;
}

function getConfidenceLabel(confidence: number) {
  if (confidence >= 0.8) {
    return "high confidence";
  }

  if (confidence >= 0.62) {
    return "medium confidence";
  }

  return "low confidence";
}

function getGroupConfidence(evidence: AspectSentiment[]) {
  const averageConfidence =
    evidence.reduce((total, aspect) => total + aspect.confidence, 0) /
    evidence.length;

  return getConfidenceLabel(averageConfidence);
}

function inferEvidenceMeaning(evidence: AspectSentiment[]) {
  const combinedText = evidence
    .map((aspect) => aspect.sentence.toLowerCase())
    .join(" ");
  const negativeCount = evidence.filter(
    (aspect) => aspect.sentiment === "negative"
  ).length;
  const positiveCount = evidence.filter(
    (aspect) => aspect.sentiment === "positive"
  ).length;

  if (
    /\b(never ran out|works very well|works well|well-made|reliable|nothing bad|fine job|better than)\b/.test(
      combinedText
    )
  ) {
    return {
      signal: "Positive or precautionary",
      meaning:
        "The customer is discussing this topic, but the wording does not describe a failure. It reads as positive feedback or a precaution.",
    };
  }

  if (
    /\b(extra battery|spare battery|backup battery|concerned about using all|just in case)\b/.test(
      combinedText
    )
  ) {
    return {
      signal: "Precautionary",
      meaning:
        "The customer is planning around battery use or keeping a backup. This is topic-relevant, but it is not clearly a product defect.",
    };
  }

  if (
    negativeCount > positiveCount ||
    /\b(losing power|lost power|died|dies|dead|not charging|won't charge|doesn't charge|ran out|drain|drains|problem|issue|failed|failure)\b/.test(
      combinedText
    )
  ) {
    return {
      signal: "Potential issue",
      meaning:
        "The customer may be describing a problem or concern. This evidence should be reviewed as a possible complaint.",
    };
  }

  if (positiveCount > negativeCount) {
    return {
      signal: "Positive feedback",
      meaning:
        "The customer is discussing this topic in a favorable way. Treat it as relevant context, not a complaint.",
    };
  }

  return {
    signal: "Needs auditor review",
    meaning:
      "The sentence is related to the topic, but the wording is not clear enough for the system to classify it as positive or negative.",
  };
}

function getEvidenceGroups(aspects: AspectSentiment[]) {
  const groups = new Map<string, AspectSentiment[]>();

  for (const aspect of getUsefulEvidence(aspects)) {
    const topic = getTopicLabel(aspect.aspect);
    const existing = groups.get(topic) ?? [];
    existing.push(aspect);
    groups.set(topic, existing);
  }

  return Array.from(groups.entries()).map(([topic, evidence]) => {
    const { signal, meaning } = inferEvidenceMeaning(evidence);
    const categories = uniqueValues(
      evidence.map((aspect) => aspect.category ?? "uncategorized")
    );

    return {
      topic,
      category: categories.map(formatCategory).join(", "),
      evidence: evidence.slice(0, 2),
      signal,
      meaning,
      confidence: getGroupConfidence(evidence),
    };
  });
}

function getPrimaryEvidence(evidence: AspectSentiment[]) {
  return (
    evidence.find((aspect) =>
      /\b(never ran out|works very well|works well|fine job|losing power|lost power|not charging|won't charge|doesn't charge|died|dead|extra battery|spare battery|backup battery)\b/i.test(
        aspect.sentence
      )
    ) ??
    evidence.find((aspect) => aspect.sentiment !== "neutral") ??
    evidence[0]
  );
}

function getRelevanceLabel(score: number) {
  if (score >= 0.75) {
    return "High";
  }

  if (score >= 0.45) {
    return "Medium";
  }

  return "Low";
}

function getAuditSummary(result: ReviewResult, query: string) {
  const visibleAspects = getUsefulEvidence(result.aspects).slice(0, 4);
  const names = uniqueValues(
    visibleAspects.map((aspect) => getTopicLabel(aspect.aspect))
  );
  const negativeScore = visibleAspects
    .filter((aspect) => aspect.sentiment === "negative")
    .reduce((total, aspect) => total + aspect.confidence, 0);
  const positiveScore = visibleAspects
    .filter((aspect) => aspect.sentiment === "positive")
    .reduce((total, aspect) => total + aspect.confidence, 0);
  const primaryEvidence = getPrimaryEvidence(visibleAspects);

  if (visibleAspects.length === 0) {
    const excerpt =
      result.text.length > 240 ? `${result.text.slice(0, 240)}...` : result.text;

    return {
      summary:
        "This review matched the search, but the system did not extract a specific product topic.",
      topics: "General review",
      sentiment: "Needs auditor review",
      mainEvidence: excerpt,
      whyMatched: `Returned because it matched the search query "${query}".`,
    };
  }

  const topicText = toListText(names);
  const inferredMeaning = inferEvidenceMeaning(visibleAspects);
  const sentiment =
    negativeScore > positiveScore
      ? "Potential customer issue"
      : positiveScore > negativeScore
        ? "Positive customer feedback"
        : negativeScore > 0 && positiveScore > 0
          ? "Mixed customer feedback"
          : inferredMeaning.signal;
  const summary =
    negativeScore > positiveScore
      ? `This review may indicate a customer concern about ${topicText}.`
      : positiveScore > negativeScore
        ? `This review appears favorable and discusses ${topicText}.`
        : negativeScore > 0 && positiveScore > 0
          ? `This review discusses ${topicText} with mixed positive and negative signals.`
          : inferredMeaning.signal === "Positive or precautionary"
            ? `This review discusses ${topicText}, but it appears positive or precautionary rather than a complaint.`
            : inferredMeaning.signal === "Precautionary"
              ? `This review discusses ${topicText} as a precaution or backup purchase, not a clear product failure.`
              : inferredMeaning.signal === "Potential issue"
                ? `This review may indicate a customer concern about ${topicText}.`
                : `This review discusses ${topicText}, but the extracted evidence is not clearly positive or negative.`;
  const whyMatched =
    negativeScore > positiveScore
      ? `Returned because "${query}" is related to ${topicText}, and the evidence may indicate a customer concern.`
      : positiveScore > negativeScore
        ? `Returned because "${query}" is related to ${topicText}. The review is mostly positive, so treat it as a relevant non-complaint or comparison result.`
        : negativeScore > 0 && positiveScore > 0
          ? `Returned because "${query}" is related to ${topicText}. The review has mixed signals, so inspect the evidence before classifying it.`
          : inferredMeaning.signal === "Positive or precautionary" ||
              inferredMeaning.signal === "Precautionary"
            ? `Returned because "${query}" is related to ${topicText}. The evidence is relevant, but it reads as positive or precautionary rather than a complaint.`
            : `Returned because "${query}" is related to ${topicText}. The evidence is topic-relevant, but the sentiment needs auditor review.`;

  return {
    summary,
    topics: topicText,
    sentiment,
    mainEvidence: primaryEvidence.sentence,
    whyMatched,
  };
}

export default function Home() {
  const [query, setQuery] = useState("battery issues");
  const [limit, setLimit] = useState(10);
  const [data, setData] = useState<SearchResponse | null>(null);
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);
  const [expandedReviewIds, setExpandedReviewIds] = useState<Set<number>>(
    () => new Set()
  );
  const [expandedEvidenceIds, setExpandedEvidenceIds] = useState<Set<number>>(
    () => new Set()
  );

  const summary = useMemo(() => {
    const results = data?.results ?? [];

    return {
      count: results.length,
      averageSearchScore:
        results.length === 0
          ? 0
          : results.reduce((total, item) => total + item.relevance, 0) /
            results.length,
      aspectCount: results.reduce(
        (total, item) => total + item.aspects.length,
        0
      ),
    };
  }, [data]);

  async function onSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setLoading(true);
    setError("");
    setExpandedReviewIds(new Set());
    setExpandedEvidenceIds(new Set());

    try {
      const response = await fetch(
        `/api/search?q=${encodeURIComponent(query)}&limit=${limit}`
      );
      const payload = await response.json();

      if (!response.ok) {
        throw new Error(payload.error ?? "Search failed.");
      }

      setData(payload);
    } catch (searchError) {
      setData(null);
      setError(
        searchError instanceof Error ? searchError.message : "Search failed."
      );
    } finally {
      setLoading(false);
    }
  }

  function toggleReview(reviewId: number) {
    setExpandedReviewIds((current) => {
      const next = new Set(current);

      if (next.has(reviewId)) {
        next.delete(reviewId);
      } else {
        next.add(reviewId);
      }

      return next;
    });
  }

  function toggleEvidence(reviewId: number) {
    setExpandedEvidenceIds((current) => {
      const next = new Set(current);

      if (next.has(reviewId)) {
        next.delete(reviewId);
      } else {
        next.add(reviewId);
      }

      return next;
    });
  }

  return (
    <main className="shell">
      <section className="toolbar" aria-label="Search controls">
        <div>
          <p className="eyebrow">Review Intelligence</p>
          <h1>Amazon opinion search</h1>
        </div>

        <form className="searchForm" onSubmit={onSubmit}>
          <label className="queryLabel" htmlFor="query">
            Query
          </label>
          <input
            id="query"
            name="query"
            value={query}
            onChange={(event) => setQuery(event.target.value)}
            placeholder="battery life, screen quality, charger problems"
          />

          <label className="limitLabel" htmlFor="limit">
            Results
          </label>
          <input
            id="limit"
            min={1}
            max={25}
            type="number"
            value={limit}
            onChange={(event) => setLimit(Number(event.target.value))}
          />

          <button type="submit" disabled={loading}>
            {loading ? "Searching" : "Search"}
          </button>
        </form>
      </section>

      <section className="metrics" aria-label="Search metrics">
        <div>
          <span>Results</span>
          <strong>{summary.count}</strong>
        </div>
        <div>
          <span>Avg relevance</span>
          <strong>{summary.averageSearchScore.toFixed(3)}</strong>
        </div>
        <div>
          <span>Evidence sentences</span>
          <strong>{summary.aspectCount}</strong>
        </div>
      </section>

      {error ? <p className="error">{error}</p> : null}

      <section className="results" aria-label="Search results">
        {(data?.results ?? []).map((result, index) => {
          const auditSummary = getAuditSummary(result, data?.query ?? query);
          const evidenceGroups = getEvidenceGroups(result.aspects);
          const detailedEvidenceOpen = expandedEvidenceIds.has(result.id);
          const relevanceLabel = getRelevanceLabel(result.relevance);

          return (
            <article className="result" key={result.id}>
            <div className="resultHeader">
              <div>
                <span className="rank">#{index + 1}</span>
                <h2>{result.title || "Untitled review"}</h2>
              </div>
              <div className="score">
                <span>Relevance</span>
                <strong>{relevanceLabel}</strong>
                <small>{result.relevance.toFixed(3)}</small>
              </div>
            </div>

            <div className="meta">
              <span>
                <strong>Product ID</strong>
                {result.productId ?? "Unknown"}
              </span>
              <span>
                <strong>Customer rating</strong>
                {result.rating ? `${result.rating} out of 5 stars` : "Not available"}
              </span>
              <span>
                <strong>Review date</strong>
                {result.writtenDate ?? "Not available"}
              </span>
              <span>
                <strong>Purchase status</strong>
                {result.verifiedPurchase
                  ? "Verified Amazon purchase"
                  : "Not verified or unknown"}
              </span>
            </div>

            <section className="auditSummary" aria-label="Audit summary">
              <div className="summaryPrimary">
                <span>Audit summary</span>
                <strong>{auditSummary.summary}</strong>
              </div>
              <div>
                <span>Detected topics</span>
                <strong>{auditSummary.topics}</strong>
              </div>
              <div>
                <span>Customer signal</span>
                <strong>{auditSummary.sentiment}</strong>
              </div>
            </section>

            <section className="mainEvidence" aria-label="Main evidence">
              <div>
                <span>Key evidence</span>
                <p>{auditSummary.mainEvidence}</p>
              </div>
              <div>
                <span>Why this appeared</span>
                <p>{auditSummary.whyMatched}</p>
              </div>
            </section>

            {evidenceGroups.length > 0 ? (
              <>
                <button
                  className="textButton evidenceButton"
                  type="button"
                  onClick={() => toggleEvidence(result.id)}
                >
                  {detailedEvidenceOpen
                    ? "Hide detailed evidence"
                    : `Show detailed evidence (${evidenceGroups.length})`}
                </button>

                {detailedEvidenceOpen ? (
                  <div className="evidenceGroups">
                    {evidenceGroups.map((group) => (
                      <section className="evidenceGroup" key={group.topic}>
                        <div className="evidenceGroupHeader">
                          <div>
                            <span>Topic</span>
                            <strong>{group.topic}</strong>
                          </div>
                          <div>
                            <span>Category</span>
                            <strong>{group.category}</strong>
                          </div>
                        </div>

                        <div className="evidenceGroupBody">
                          <div>
                            <span>What the customer said</span>
                            {group.evidence.map((aspect, index) => (
                              <p key={`${group.topic}-${index}-${aspect.sentence.slice(0, 24)}`}>
                                {aspect.sentence}
                              </p>
                            ))}
                          </div>

                          <div>
                            <span>What this means</span>
                            <p>{group.meaning}</p>
                          </div>
                        </div>

                        <div className="evidenceDecision">
                          <span>Customer signal</span>
                          <strong>{group.signal}</strong>
                          <small>{group.confidence}</small>
                        </div>
                      </section>
                    ))}
                  </div>
                ) : null}
              </>
            ) : null}

            <p className="reviewLabel">Original review</p>
            <p
              className={
                expandedReviewIds.has(result.id)
                  ? "reviewText expanded"
                  : "reviewText"
              }
            >
              {result.text}
            </p>

            {result.text.length > 700 ? (
              <button
                className="textButton"
                type="button"
                onClick={() => toggleReview(result.id)}
              >
                {expandedReviewIds.has(result.id)
                  ? "Show less"
                  : "Read full review"}
              </button>
            ) : null}
            </article>
          );
        })}

        {!loading && data && data.results.length === 0 ? (
          <p className="empty">No matching reviews found.</p>
        ) : null}
      </section>
    </main>
  );
}
