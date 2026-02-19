import re


def normalize_name(value: str) -> str:
    upper = value.strip().upper()
    # Convert hyphens to underscores first
    upper = upper.replace("-", "_")
    # Remove any special characters except underscores and spaces
    upper = re.sub(r"[^A-Z0-9\s_]", "", upper)
    # Convert spaces to underscores
    upper = re.sub(r"\s+", "_", upper)
    # Collapse multiple underscores
    upper = re.sub(r"_+", "_", upper)
    return upper.strip("_")


def build_branch_name(team_name: str, leader_name: str) -> str:
    team = normalize_name(team_name)
    leader = normalize_name(leader_name)
    if not team or not leader:
        raise ValueError("Team name and leader name are required for branch naming.")
    return f"{team}_{leader}_AI_Fix"


def validate_commit_prefix(message: str) -> bool:
    return message.startswith("[AI-AGENT]")


def ensure_commit_prefix(message: str) -> str:
    if validate_commit_prefix(message):
        return message
    return f"[AI-AGENT] {message}"
