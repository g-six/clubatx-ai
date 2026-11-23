"""Check independently observed module coverage against an intended/readback bundle."""
import argparse
import json

def resolve(document, path):
    if not isinstance(path, str) or not path.startswith("/"):
        raise ValueError("A captured module needs an absolute JSON pointer")
    for key in path[1:].split("/"):
        key = key.replace("~1", "/").replace("~0", "~")
        document = document[int(key)] if isinstance(document, list) else document[key]
    return document

def validate_capture(manifest, bundle):
    if not isinstance(manifest, list) or not manifest:
        raise ValueError("Coverage inventory must not be empty")
    for item in manifest:
        module = item.get("module", "unknown module")
        if not item.get("source_url"):
            raise ValueError(module + ": source provenance missing")
        if item.get("status") == "unavailable":
            if not str(item.get("reason", "")).strip():
                raise ValueError(module + ": unavailable reason missing")
            continue
        if item.get("status") != "captured" or "expected" not in item:
            raise ValueError(module + ": capture is incomplete")
        try:
            actual = resolve(bundle, item.get("path"))
        except (ValueError, KeyError, IndexError, TypeError) as error:
            raise ValueError(module + ": intended database field missing") from error
        if actual != item["expected"]:
            raise ValueError(module + ": intended/readback value differs from verified capture")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("manifest")
    parser.add_argument("bundle")
    args = parser.parse_args()
    with open(args.manifest) as source: manifest = json.load(source)
    with open(args.bundle) as source: bundle = json.load(source)
    validate_capture(manifest, bundle)
    print("Every inventoried module saved exactly or explicitly unavailable")
