import { readFileSync } from "node:fs";
import mysql, { type Pool } from "mysql2/promise";

let pool: Pool | undefined;

function normalizeCertificate(value: string) {
  return value.trim().replace(/\\n/g, "\n").replace(/\\/g, "\n");
}

function looksLikeCertificate(value: string) {
  return value.includes("-----BEGIN CERTIFICATE-----");
}

function getSslConfig() {
  const ca = (
    process.env.MYSQL_CA_CERT ?? process.env.MYSQL_SSL_CA_CONTENT
  )?.trim();
  const caPath = process.env.MYSQL_CA_CERT_PATH?.trim();

  if (ca) {
    return {
      ca: normalizeCertificate(ca),
      rejectUnauthorized: true,
    };
  }

  if (caPath) {
    if (looksLikeCertificate(caPath)) {
      return {
        ca: normalizeCertificate(caPath),
        rejectUnauthorized: true,
      };
    }

    return {
      ca: readFileSync(caPath, "utf8"),
      rejectUnauthorized: true,
    };
  }

  return {
    rejectUnauthorized: process.env.MYSQL_SSL_REJECT_UNAUTHORIZED !== "false",
  };
}

export function getPool() {
  if (!process.env.DATABASE_URL) {
    throw new Error("DATABASE_URL is not configured.");
  }

  if (!pool) {
    pool = mysql.createPool({
      uri: process.env.DATABASE_URL,
      database: process.env.MYSQL_DATABASE || "review_intelligence",
      ssl: getSslConfig(),
      waitForConnections: true,
      connectionLimit: 5,
      namedPlaceholders: true,
    });
  }

  return pool;
}
