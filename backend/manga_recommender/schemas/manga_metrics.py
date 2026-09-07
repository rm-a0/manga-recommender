"""Response models for the rating metrics derived from a manga's external ratings."""

import uuid

from pydantic import BaseModel


class MangaMetricSummary(BaseModel):
    """A manga's rating metrics as they appear embedded in a manga response.

    Carries the score to show and the vote count that qualifies it. The
    `mean_score`, `source_count` and `computed_at` on the row describe how the
    score was computed rather than what to render, so they stay out.

    Metrics have no endpoint of their own; a manga with no usable source rating
    has no metrics row at all, so the embedding field is None.
    """

    id: uuid.UUID
    bayesian_score: float
    votes_count: int
