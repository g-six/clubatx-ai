import unittest
from validate_capture import validate_capture

class CaptureTests(unittest.TestCase):
    def entry(self, **changes):
        return dict(module="AI bullets",status="captured",source_url="https://app.veo.co/matches/example/report/",path="/payload/analysis_reports",expected=[{"blocks":[{"type":"bullet","text":"Original"}]}],**changes)
    def test_missing_bullets_blocks_complete_import(self):
        with self.assertRaisesRegex(ValueError,"field missing"):
            validate_capture([self.entry()],{"payload":{}})
    def test_changed_bullet_blocks_complete_import(self):
        with self.assertRaisesRegex(ValueError,"differs"):
            validate_capture([self.entry()],{"payload":{"analysis_reports":[]}})
    def test_exact_bullets_and_zero_player_stat_pass(self):
        e=self.entry()
        player=dict(module="Matches",status="captured",source_url=e["source_url"],path="/players/0/matches",expected=0)
        validate_capture([e,player],{"payload":{"analysis_reports":e["expected"]},"players":[{"matches":0}]})
    def test_unavailable_requires_observed_reason(self):
        entry={"module":"Opponent player stats","status":"unavailable","source_url":"https://app.veo.co"}
        with self.assertRaisesRegex(ValueError,"reason missing"): validate_capture([entry],{})
        entry["reason"]="Rendered module says player stats unavailable for opponent teams"
        validate_capture([entry],{})
    def test_pending_cannot_be_reported_complete(self):
        entry=self.entry();entry["status"]="pending"
        with self.assertRaisesRegex(ValueError,"incomplete"):validate_capture([entry],{})

if __name__=="__main__":unittest.main()
