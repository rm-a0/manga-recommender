"""Query AniList for the community recommendations of each manga."""

from typing import Any

from manga_recommender.ingestion.anilist.client import AnilistClient

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
    """Return the raw record of each manga in `ids` that has recommendations.

    Raise when the query fails. The caller decides what a failed chunk means.
    """
    data = await client.execute(
        query=RECOMMENDATIONS_QUERY, variables={"ids": ids, "perPage": len(ids)}
    )
    return [media for media in data["Page"]["media"] if _has_recommendations(media)]


def _has_recommendations(media: dict[str, Any]) -> bool:
    return bool((media.get("recommendations") or {}).get("nodes"))
