"""Filter a verified normalized passing network; stdin JSON -> stdout JSON."""
import copy
import json
import sys


def filter_network(network):
    result = copy.deepcopy(network)
    nodes = result["nodes"]
    edges = result["edges"]
    jerseys = {n["jersey_number"] for n in nodes}
    retained = []
    for edge in edges:
        count = edge.get("completed_passes")
        if type(count) is not int or count < 0:
            raise ValueError("Every connection needs a verified non-negative integer completed_passes count")
        if edge.get("from_jersey") not in jerseys or edge.get("to_jersey") not in jerseys:
            raise ValueError("Every connection must reference verified nodes")
        if count > 3:
            retained.append(edge)
    used = {e[k] for e in retained for k in ("from_jersey", "to_jersey")}
    result["edges"] = retained
    result["nodes"] = [n for n in nodes if n["jersey_number"] in used]
    return result


if __name__ == "__main__":
    json.dump(filter_network(json.load(sys.stdin)), sys.stdout, allow_nan=False)
    sys.stdout.write("\n")
