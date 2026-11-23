"""Reject silent loss of optional payload data before an import preview."""
import argparse
import json

CORE_TOP = {"match", "teams", "key_events"}
CORE_TEAM = {"possession_percent", "completed_passes", "passes_by_third", "events", "attempt_locations", "momentum_percent"}

def pointer(*parts):
    return "/" + "/".join(str(p).replace("~", "~0").replace("/", "~1") for p in parts)

def validate_preservation(before, after, refreshed=()):
    extensions = [(pointer(k), v, after.get(k)) for k, v in before.items() if k not in CORE_TOP]
    for team, value in before.get("teams", {}).items():
        for key, original in value.items():
            if key not in CORE_TEAM:
                extensions.append((pointer("teams", team, key), original, after.get("teams", {}).get(team, {}).get(key)))
    errors = []
    for path, original, candidate in extensions:
        if candidate is None and original is not None:
            errors.append(path + " is missing")
        elif candidate != original and path not in refreshed:
            errors.append(path + " changed without a verified refresh")
        elif original and not candidate:
            errors.append(path + " was cleared")
    if errors:
        raise ValueError("; ".join(errors))

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("before")
    parser.add_argument("after")
    parser.add_argument("--refreshed", action="append", default=[])
    args = parser.parse_args()
    with open(args.before) as source: before = json.load(source)
    with open(args.after) as source: after = json.load(source)
    validate_preservation(before, after, args.refreshed)
    print("Existing optional fields preserved or explicitly source-refreshed")
