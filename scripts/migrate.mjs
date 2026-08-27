import { readFileSync } from "node:fs";
import { readFile } from "node:fs/promises";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";
import nextEnv from "@next/env";
import mysql from "mysql2/promise";

const __dirname = dirname(fileURLToPath(import.meta.url));
const projectRoot = join(__dirname, "..");
const { loadEnvConfig } = nextEnv;

loadEnvConfig(projectRoot);

const schemaPath = join(projectRoot, "database", "schema.sql");
const databaseName = process.env.MYSQL_DATABASE || "review_intelligence";

const databaseUrl = process.env.DATABASE_URL;

if (!databaseUrl) {
  console.error("DATABASE_URL is required.");
  process.exit(1);
}

function getServerConnectionUrl(url) {
  const serverUrl = new URL(url);
  serverUrl.pathname = "/";
  return serverUrl.toString();
}

function getSslConfig() {
  const ca = process.env.MYSQL_CA_CERT?.trim();
  const caPath = process.env.MYSQL_CA_CERT_PATH?.trim();

  if (ca) {
    return {
      ca: ca.replace(/\\n/g, "\n").replace(/\\/g, "\n"),
      rejectUnauthorized: true,
    };
  }

  if (caPath) {
    return {
      ca: readFileSync(caPath, "utf8"),
      rejectUnauthorized: true,
    };
  }

  return {
    rejectUnauthorized: process.env.MYSQL_SSL_REJECT_UNAUTHORIZED !== "false",
  };
}

const connection = await mysql.createConnection({
  uri: getServerConnectionUrl(databaseUrl),
  multipleStatements: true,
  ssl: getSslConfig(),
});

try {
  const schemaSql = await readFile(schemaPath, "utf8");
  const escapedDatabaseName = databaseName.replaceAll("`", "``");

  await connection.query(
    `
      CREATE DATABASE IF NOT EXISTS \`${escapedDatabaseName}\`
      CHARACTER SET utf8mb4
      COLLATE utf8mb4_unicode_ci
    `
  );
  await connection.query(`USE \`${escapedDatabaseName}\``);
  await connection.query(schemaSql);
  console.log(`Database schema migration completed for ${databaseName}.`);
} finally {
  await connection.end();
}
