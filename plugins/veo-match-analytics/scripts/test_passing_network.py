import copy
import unittest
from passing_network import filter_network

class PassingNetworkTests(unittest.TestCase):
    def setUp(self):
        self.graph = {"nodes": [{"jersey_number": n} for n in range(7)], "edges": [
            {"from_jersey": 0, "to_jersey": n + 1, "completed_passes": n} for n in range(6)]}
    def test_strict_boundary_and_unused_nodes(self):
        original = copy.deepcopy(self.graph)
        result = filter_network(self.graph)
        self.assertEqual([e["completed_passes"] for e in result["edges"]], [4, 5])
        self.assertEqual([n["jersey_number"] for n in result["nodes"]], [0, 5, 6])
        self.assertEqual(self.graph, original)
    def test_reverse_connections_do_not_combine(self):
        self.graph["edges"] = [{"from_jersey": a, "to_jersey": b, "completed_passes": 2} for a,b in [(0,1),(1,0)]]
        self.assertEqual(filter_network(self.graph)["edges"], [])
        self.assertEqual(filter_network(self.graph)["nodes"], [])
    def test_unknown_count_is_not_silently_recorded(self):
        for count in [None, True, 4.1, -1, "4"]:
            self.graph["edges"][0]["completed_passes"] = count
            with self.assertRaises(ValueError): filter_network(self.graph)
    def test_legacy_visual_edges_need_source_counts(self):
        self.graph["edges"] = [{"x1": .1, "x2": .2, "width": 4}]
        with self.assertRaises(ValueError): filter_network(self.graph)

if __name__ == "__main__": unittest.main()
