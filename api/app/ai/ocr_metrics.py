"""Validation numbers for the intake pipeline: character error rate and seconds per page by route."""


def cer(reference, hypothesis):
    """Levenshtein distance over characters divided by the reference length; whitespace is ignored."""
    reference, hypothesis = "".join(reference.split()), "".join(hypothesis.split())
    if not reference:
        return 0.0 if not hypothesis else 1.0
    previous = list(range(len(hypothesis) + 1))
    for i, expected in enumerate(reference, 1):
        current = [i]
        for j, got in enumerate(hypothesis, 1):
            current.append(min(previous[j] + 1, current[j - 1] + 1, previous[j - 1] + (expected != got)))
        previous = current
    return previous[-1] / len(reference)


def accuracy(reference, hypothesis):
    return max(0.0, 1 - cer(reference, hypothesis))


def route_stats(pages):
    stats = {}
    for page in pages:
        item = stats.setdefault(page.route, {"pages": 0, "seconds": 0.0})
        item["pages"] += 1
        item["seconds"] = round(item["seconds"] + page.seconds, 3)
    for item in stats.values():
        item["per_page"] = round(item["seconds"] / item["pages"], 3)
    return stats
