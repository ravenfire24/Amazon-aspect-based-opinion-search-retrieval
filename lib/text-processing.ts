export type SemanticProfile = {
  name: string;
  aliases: string[];
};

const STOP_WORDS = new Set([
  "a",
  "an",
  "and",
  "are",
  "as",
  "at",
  "be",
  "but",
  "by",
  "for",
  "from",
  "had",
  "has",
  "have",
  "i",
  "in",
  "is",
  "it",
  "its",
  "my",
  "of",
  "on",
  "or",
  "our",
  "so",
  "that",
  "the",
  "their",
  "this",
  "to",
  "was",
  "were",
  "with",
  "you",
  "your",
]);

export const SEMANTIC_PROFILES: SemanticProfile[] = [
  {
    name: "battery life",
    aliases: [
      "battery",
      "batteries",
      "charge",
      "charged",
      "charging",
      "drain",
      "drains",
      "died",
      "dies",
      "lasting",
      "lasts",
      "longevity",
      "power",
      "recharge",
      "runtime",
    ],
  },
  {
    name: "charger",
    aliases: ["adapter", "base", "cable", "charger", "cord", "dock", "plug"],
  },
  {
    name: "software",
    aliases: [
      "app",
      "application",
      "driver",
      "firmware",
      "program",
      "software",
      "update",
      "updates",
    ],
  },
  {
    name: "user interface",
    aliases: [
      "button",
      "buttons",
      "controls",
      "interface",
      "menu",
      "menus",
      "navigation",
      "ui",
    ],
  },
  {
    name: "ease of use",
    aliases: [
      "confusing",
      "easy",
      "install",
      "installation",
      "intuitive",
      "manual",
      "setup",
      "simple",
      "usable",
    ],
  },
  {
    name: "performance",
    aliases: [
      "crash",
      "crashes",
      "fast",
      "freeze",
      "freezes",
      "lag",
      "laggy",
      "performance",
      "responsive",
      "slow",
      "speed",
    ],
  },
  {
    name: "screen",
    aliases: [
      "backlight",
      "brightness",
      "display",
      "lcd",
      "resolution",
      "screen",
      "viewing",
    ],
  },
  {
    name: "sound quality",
    aliases: [
      "audio",
      "earbuds",
      "headphones",
      "loud",
      "speaker",
      "speakers",
      "sound",
      "volume",
    ],
  },
  {
    name: "camera quality",
    aliases: [
      "camera",
      "flash",
      "lens",
      "photo",
      "photos",
      "picture",
      "pictures",
      "video",
    ],
  },
  {
    name: "build quality",
    aliases: [
      "build",
      "cover",
      "durability",
      "durable",
      "fragile",
      "material",
      "plastic",
      "quality",
      "solid",
      "sturdy",
    ],
  },
  {
    name: "fit and comfort",
    aliases: [
      "comfort",
      "comfortable",
      "fit",
      "heavy",
      "light",
      "size",
      "snug",
      "weight",
    ],
  },
  {
    name: "price and value",
    aliases: [
      "cheap",
      "cost",
      "deal",
      "expensive",
      "money",
      "price",
      "value",
      "worth",
    ],
  },
  {
    name: "connectivity",
    aliases: [
      "bluetooth",
      "connect",
      "connection",
      "pair",
      "pairing",
      "signal",
      "usb",
      "wifi",
      "wireless",
    ],
  },
  {
    name: "storage and memory",
    aliases: ["capacity", "card", "gb", "mb", "memory", "sd", "storage"],
  },
  {
    name: "customer support",
    aliases: [
      "refund",
      "replace",
      "replacement",
      "returned",
      "service",
      "support",
      "warranty",
    ],
  },
];

const ALIAS_TO_PROFILE = new Map(
  SEMANTIC_PROFILES.flatMap((profile) =>
    profile.aliases.map((alias) => [alias, profile.name] as const)
  )
);

export function normalizeText(value: string | null | undefined) {
  if (!value) {
    return "";
  }

  return value
    .normalize("NFKC")
    .replace(/\\r\\n|\\n|\\r/g, "\n")
    .replace(/\r\n|\r/g, "\n")
    .replace(/https?:\/\/\S+/gi, " ")
    .replace(/<[^>]*>/g, " ")
    .replace(/[\u0000-\u001f\u007f]/g, " ")
    .replace(/[^a-zA-Z0-9'\s-]/g, " ")
    .replace(/-/g, " ")
    .replace(/\s+/g, " ")
    .trim()
    .toLowerCase();
}

export function tokenize(value: string) {
  const normalized = normalizeText(value);

  return normalized
    .split(" ")
    .map((token) => token.trim())
    .filter((token) => token.length >= 2 && !STOP_WORDS.has(token));
}

export function inferSemanticProfiles(value: string) {
  const normalized = normalizeText(value);
  const tokens = new Set(tokenize(normalized));
  const matches = new Set<string>();

  for (const profile of SEMANTIC_PROFILES) {
    if (normalized.includes(profile.name)) {
      matches.add(profile.name);
      continue;
    }

    if (
      profile.aliases.some((alias) =>
        alias.includes(" ") ? normalized.includes(alias) : tokens.has(alias)
      )
    ) {
      matches.add(profile.name);
    }
  }

  return Array.from(matches);
}

export function expandSearchTerms(value: string) {
  const terms = new Set(tokenize(value));

  for (const profileName of inferSemanticProfiles(value)) {
    const profile = SEMANTIC_PROFILES.find((item) => item.name === profileName);

    if (!profile) {
      continue;
    }

    for (const part of tokenize(profile.name)) {
      terms.add(part);
    }

    for (const alias of profile.aliases) {
      terms.add(alias);
    }
  }

  return Array.from(terms).filter((term) => term.length >= 3).slice(0, 48);
}

export function buildSemanticVector(value: string) {
  const vector = new Map<string, number>();
  const normalized = normalizeText(value);

  for (const token of tokenize(normalized)) {
    const canonical = ALIAS_TO_PROFILE.get(token);

    vector.set(token, (vector.get(token) ?? 0) + 1);

    if (canonical) {
      vector.set(`aspect:${canonical}`, (vector.get(`aspect:${canonical}`) ?? 0) + 2);
    }
  }

  for (const profileName of inferSemanticProfiles(normalized)) {
    vector.set(`aspect:${profileName}`, (vector.get(`aspect:${profileName}`) ?? 0) + 3);
  }

  return vector;
}

export function cosineSimilarity(
  left: Map<string, number>,
  right: Map<string, number>
) {
  let dot = 0;
  let leftMagnitude = 0;
  let rightMagnitude = 0;

  for (const value of left.values()) {
    leftMagnitude += value * value;
  }

  for (const value of right.values()) {
    rightMagnitude += value * value;
  }

  for (const [key, value] of left) {
    dot += value * (right.get(key) ?? 0);
  }

  if (leftMagnitude === 0 || rightMagnitude === 0) {
    return 0;
  }

  return dot / (Math.sqrt(leftMagnitude) * Math.sqrt(rightMagnitude));
}
