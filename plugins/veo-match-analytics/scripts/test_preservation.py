import copy
import unittest
from validate_preservation import validate_preservation

class PreservationTests(unittest.TestCase):
    def setUp(self):
        self.before = {"match": {}, "key_events": [], "analysis_reports": [{"blocks": [{"type":"bullet","text":"Veo insight"}]}], "teams": {"PF": {"passing_network": {"nodes": [28], "edges": [4]}}}}
    def test_intact_extensions_survive_core_refresh(self):
        after = copy.deepcopy(self.before)
        after["key_events"] = [{"sequence": 0}]
        validate_preservation(self.before, after)
    def test_core_only_replacement_rejects_both_missing_extensions(self):
        with self.assertRaisesRegex(ValueError, "analysis_reports.*passing_network"):
            validate_preservation(self.before, {"match": {}, "key_events": [], "teams": {"PF": {}}})
    def test_unacknowledged_report_rewrite_rejected(self):
        after = copy.deepcopy(self.before)
        after["analysis_reports"][0]["blocks"][0]["text"] = "Changed"
        with self.assertRaisesRegex(ValueError, "changed without"):
            validate_preservation(self.before, after)
    def test_explicit_refresh_cannot_remove_reports(self):
        after = copy.deepcopy(self.before)
        after["analysis_reports"] = []
        with self.assertRaisesRegex(ValueError, "cleared"):
            validate_preservation(self.before, after, ["/analysis_reports"])
    def test_verified_graph_refresh_is_allowed(self):
        after = copy.deepcopy(self.before)
        after["teams"]["PF"]["passing_network"]["edges"] = [5]
        validate_preservation(self.before, after, ["/teams/PF/passing_network"])

if __name__ == "__main__": unittest.main()
