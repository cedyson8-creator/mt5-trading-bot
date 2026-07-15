def validate_selected_symbols(connector, pairs, strict_symbols=False):
    valid_pairs, warnings, fatal_issues = connector.validate_symbols(pairs, strict=strict_symbols)
    if not valid_pairs:
        fatal_issues = list(fatal_issues) + ["No valid trading pairs remain after validation"]
    return valid_pairs, warnings, fatal_issues


def run_startup_checks(connector, pairs, strict_symbols=False):
    return connector.startup_check(pairs, strict_symbols=strict_symbols)


def log_issues(log, title, issues, level="error"):
    if not issues:
        return
    getattr(log, level)(title)
    for issue in issues:
        getattr(log, level)(f"  - {issue}")
