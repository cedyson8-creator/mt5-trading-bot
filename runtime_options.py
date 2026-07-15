import config
from pair_utils import resolve_pairs_and_sources


def resolve_runtime_options(args):
    runtime_dry_run = config.DRY_RUN
    if getattr(args, "dry_run", False):
        runtime_dry_run = True
    elif getattr(args, "live", False):
        runtime_dry_run = False

    runtime_pairs, pair_sources = resolve_pairs_and_sources(
        cli_pairs=getattr(args, "pair_list", None),
        pairs_csv=getattr(args, "pairs_csv", None),
        pairs_file=getattr(args, "pairs_file", None),
    )

    config.DRY_RUN = runtime_dry_run
    config.PAIRS = runtime_pairs
    return runtime_dry_run, runtime_pairs, pair_sources


def format_symbol_listing(runtime_pairs, pair_sources):
    return "\n".join(
        f"{pair}  [{', '.join(pair_sources.get(pair, ['unknown']))}]"
        for pair in runtime_pairs
    )
