import { getPool } from "@/lib/db";
import type { RowDataPacket } from "mysql2";

interface HealthRow extends RowDataPacket {
  read_only: number;
  indexed_datasets: number;
  indexed_reviews: number;
}

export async function GET() {
  try {
    const pool = getPool();
    const [rows] = await pool.query<HealthRow[]>(
      `
        SELECT
          @@global.read_only AS read_only,
          (
            SELECT COUNT(*)
            FROM datasets
            WHERE status = 'indexed'
          ) AS indexed_datasets,
          (
            SELECT COUNT(*)
            FROM reviews r
            INNER JOIN datasets d ON d.id = r.dataset_id
            WHERE d.status = 'indexed'
          ) AS indexed_reviews
      `
    );
    const row = rows[0];

    return Response.json({
      status: "ok",
      database: "connected",
      readOnly: Boolean(row?.read_only),
      indexedDatasets: Number(row?.indexed_datasets ?? 0),
      indexedReviews: Number(row?.indexed_reviews ?? 0),
    });
  } catch (error) {
    console.error(error);

    return Response.json(
      {
        status: "error",
        database: "unavailable",
      },
      {
        status: 500,
      }
    );
  }
}
