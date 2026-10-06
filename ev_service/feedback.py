"""In-memory feedback capture for recommendation quality loops."""

from __future__ import annotations

from dataclasses import dataclass, field

from .schemas import FeedbackRecord, FeedbackRequest


@dataclass
class FeedbackStore:
    records: list[FeedbackRecord] = field(default_factory=list)

    def add(self, request: FeedbackRequest) -> FeedbackRecord:
        record = FeedbackRecord(
            feedback_id=f"feedback-{len(self.records) + 1:04d}",
            recommendation_id=request.recommendation_id,
            run_id=request.run_id,
            rating=request.rating,
            helpful=request.helpful,
            comment=request.comment.strip(),
            category=request.category,
            # Fixed demo date keeps snapshots reproducible and avoids pretending
            # the local demo has a trusted event clock.
            captured_at="2026-01-01T00:00:00Z",
        )
        self.records.append(record)
        return record

    def aggregate(self) -> dict[str, float | int]:
        if not self.records:
            return {"count": 0, "average_rating": 0.0, "helpful_rate": 0.0}
        ratings = [record.rating for record in self.records]
        helpful_values = [record.helpful for record in self.records if record.helpful is not None]
        return {
            "count": len(self.records),
            "average_rating": round(sum(ratings) / len(ratings), 3),
            "helpful_rate": round(
                sum(1 for value in helpful_values if value) / len(helpful_values), 3
            ) if helpful_values else 0.0,
        }

    def category_counts(self) -> dict[str, int]:
        counts: dict[str, int] = {}
        for record in self.records:
            counts[record.category] = counts.get(record.category, 0) + 1
        return counts
