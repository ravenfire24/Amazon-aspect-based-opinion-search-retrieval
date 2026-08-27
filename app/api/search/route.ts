import { searchReviews } from "@/lib/search";

export async function GET(request: Request) {
  const { searchParams } = new URL(request.url);
  const query = searchParams.get("q") ?? "";
  const limit = Number(searchParams.get("limit") ?? "10");

  if (!query.trim()) {
    return Response.json(
      {
        error: "Query is required.",
      },
      {
        status: 400,
      }
    );
  }

  try {
    const results = await searchReviews(query, limit);

    return Response.json({
      query,
      count: results.length,
      results,
    });
  } catch (error) {
    console.error(error);

    return Response.json(
      {
        error: "Search failed.",
      },
      {
        status: 500,
      }
    );
  }
}
