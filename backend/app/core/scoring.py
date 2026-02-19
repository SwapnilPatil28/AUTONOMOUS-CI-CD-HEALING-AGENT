from app.models.api import ScoreBreakdown


def calculate_score(duration_seconds: float | None, commit_count: int) -> ScoreBreakdown:
    base_score = 100
    speed_bonus = 10 if duration_seconds is not None and duration_seconds < 300 else 0
    efficiency_penalty = max(0, commit_count - 20) * 2
    final_score = max(0, base_score + speed_bonus - efficiency_penalty)
    return ScoreBreakdown(
        base_score=base_score,
        speed_bonus=speed_bonus,
        efficiency_penalty=efficiency_penalty,
        final_score=final_score,
    )
