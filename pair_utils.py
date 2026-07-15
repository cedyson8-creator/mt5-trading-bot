from pathlib import Path

import config


def load_pairs_file(path):
    if not path:
        return []

    file_path = Path(path)
    if not file_path.exists():
        raise FileNotFoundError(f"pairs file not found: {path}")

    pairs = []
    seen = set()
    for raw_line in file_path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue
        for item in line.split(","):
            pair = item.strip().upper()
            if pair and pair not in seen:
                seen.add(pair)
                pairs.append(pair)
    return pairs


def resolve_pairs_and_sources(cli_pairs=None, pairs_csv=None, pairs_file=None):
    resolved = []
    sources = {}
    seen = set()

    def add_pair(pair, source):
        pair = pair.strip().upper()
        if not pair:
            return
        if pair not in seen:
            seen.add(pair)
            resolved.append(pair)
            sources[pair] = [source]
        else:
            if source not in sources[pair]:
                sources[pair].append(source)

    if not cli_pairs and not pairs_csv and not pairs_file:
        for pair in config.PAIRS:
            add_pair(pair, "config")
        return resolved, sources

    for pair in cli_pairs or []:
        for item in str(pair).split(","):
            add_pair(item, "cli --pair")

    if pairs_csv:
        for item in str(pairs_csv).split(","):
            add_pair(item, "cli --pairs")

    if pairs_file:
        for item in load_pairs_file(pairs_file):
            add_pair(item, f"file {pairs_file}")

    return resolved, sources
