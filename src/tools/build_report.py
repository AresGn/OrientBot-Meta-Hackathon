def build_report(profile: dict, filieres: list[dict]) -> str:
    """Render a report where every recommendation cites its source_url."""
    if not filieres:
        return "No verified program matches this profile; no recommendation made."
    lines = [
        f"- {r['filiere']} ({r['etablissement']}) - access: {r['condition_acces']} - source: {r['source_url']}"
        for r in filieres
    ]
    return "Recommendations:\n" + "\n".join(lines)
