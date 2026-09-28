"""Query AniList for the community recommendations of each manga."""

from typing import Any

import pyarrow as pa

from manga_recommender.ingestion.anilist.client import AnilistClient

EDGE_SCHEMA = pa.schema(
    [
        ("media_id", pa.int32()),
        ("recommended_id", pa.int32()),
        ("recommended_type", pa.string()),
        ("rating", pa.int32()),
    ]
)

RECOMMENDATIONS_QUERY = """
query ($ids: [Int], $perPage: Int) {
    Page(page: 1, perPage: $perPage) {
        media(type: MANGA, id_in: $ids) { 
            id 
            recommendations(perPage: 25, sort: RATING_DESC) { 
                nodes { 
                    mediaRecommendation{ id type }
                    rating
                }
            }
        }
    }
}
"""


async def fetch_chunk(client: AnilistClient, ids: list[int]) -> list[dict[str, Any]]:
    """Return one row per recommendation of the manga in `ids`.

    Raise when the query fails. The caller decides what a failed chunk means.
    """
    data = await client.execute(
        query=RECOMMENDATIONS_QUERY, variables={"ids": ids, "perPage": len(ids)}
    )
    return [row for media in data["Page"]["media"] for row in to_edges(media)]


def to_edges(media: dict[str, Any]) -> list[dict[str, Any]]:
    """Flatten the recommendations of one manga into `EDGE_SCHEMA` rows. Keep every node."""
    rows = []
    for node in (media.get("recommendations") or {}).get("nodes") or []:
        target = node["mediaRecommendation"] or {}
        rows.append(
            {
                "media_id": media["id"],
                "recommended_id": target.get("id"),
                "recommended_type": target.get("type"),
                "rating": node["rating"],
            }
        )
    return rows
