"""
Core evaluation logic for LLM Response Quality Evaluator.
Scores responses across 5 RLHF-inspired dimensions.
"""

DIMENSIONS = [
    "instruction_following",
    "truthfulness",
    "prompt_correctness",
    "writing_quality",
    "verbosity"
]

DIMENSION_WEIGHTS = {
    "instruction_following": 1.5,  # Most critical in post-training
    "truthfulness": 1.5,
    "prompt_correctness": 1.2,
    "writing_quality": 1.0,
    "verbosity": 0.8,
}

DIMENSION_LABELS = {
    "instruction_following": "Instruction Following",
    "truthfulness": "Truthfulness",
    "prompt_correctness": "Prompt Correctness",
    "writing_quality": "Writing Quality",
    "verbosity": "Verbosity",
}


def score_responses(scores_a: dict, scores_b: dict) -> dict:
    """
    Calculate total and weighted scores for both responses.
    Returns a result dict with totals, weighted totals, and weakest dimensions.
    """
    total_a = sum(scores_a[d] for d in DIMENSIONS)
    total_b = sum(scores_b[d] for d in DIMENSIONS)

    weighted_a = sum(scores_a[d] * DIMENSION_WEIGHTS[d] for d in DIMENSIONS)
    weighted_b = sum(scores_b[d] * DIMENSION_WEIGHTS[d] for d in DIMENSIONS)

    weakest_a = min(scores_a, key=scores_a.get)
    weakest_b = min(scores_b, key=scores_b.get)

    strongest_a = max(scores_a, key=scores_a.get)
    strongest_b = max(scores_b, key=scores_b.get)

    return {
        "total_a": total_a,
        "total_b": total_b,
        "weighted_a": round(weighted_a, 2),
        "weighted_b": round(weighted_b, 2),
        "weakest_a": DIMENSION_LABELS[weakest_a],
        "weakest_b": DIMENSION_LABELS[weakest_b],
        "strongest_a": DIMENSION_LABELS[strongest_a],
        "strongest_b": DIMENSION_LABELS[strongest_b],
        "diff": abs(total_a - total_b),
    }


def get_recommendation(result: dict, scores_a: dict, scores_b: dict) -> str:
    """
    Generate a human-readable recommendation based on scores.
    Mimics the kind of feedback given in real RLHF evaluation workflows.
    """
    winner = "A" if result["weighted_a"] > result["weighted_b"] else (
        "B" if result["weighted_b"] > result["weighted_a"] else None
    )

    if winner is None:
        return (
            "Both responses are equally strong overall. "
            "Consider the specific context of the prompt to make a final call. "
            f"Response A's strength is {result['strongest_a']}, "
            f"while Response B's strength is {result['strongest_b']}."
        )

    loser = "B" if winner == "A" else "A"
    winner_scores = scores_a if winner == "A" else scores_b
    loser_scores = scores_b if winner == "A" else scores_a
    winner_weak = result[f"weakest_{'a' if winner == 'A' else 'b'}"]
    loser_weak = result[f"weakest_{'b' if winner == 'A' else 'a'}"]

    margin = result["diff"]
    if margin <= 2:
        confidence = "marginally"
    elif margin <= 5:
        confidence = "clearly"
    else:
        confidence = "significantly"

    rec = (
        f"**Response {winner}** is {confidence} better overall. "
        f"It scores higher on Instruction Following and Truthfulness — "
        f"the two most critical dimensions in post-training evaluation. "
        f"\n\nResponse {winner}'s main weakness is **{winner_weak}** — worth noting for future improvement. "
        f"\n\nResponse {loser} struggles most with **{loser_weak}**, "
        f"which explains the gap in quality."
    )

    return rec
