import unittest
from match_video_link import match_video_link

class MatchVideoLinkTests(unittest.TestCase):
    def setUp(self):
        self.report="https://app.veo.co/matches/example/#/analysis/abc?foo=1"
        self.raw="https://c.veocdn.com/example/standard/machine/id/Video.MP4?token=a%2Fb&expires=123"
    def test_match_link_is_raw_mp4_and_source_page_is_unchanged(self):
        result=match_video_link(self.report,self.raw+"#t=412.199")
        self.assertEqual(result["fixture_video_url"],self.raw)
        self.assertEqual(result["source"]["raw_video_url"],self.raw)
        self.assertEqual(result["source"]["report_url"],self.report)
        self.assertEqual(result["source"]["match_id"],"example")
    def test_rejects_page_hls_blob_and_insecure_links(self):
        for value in [self.report,"https://app.veo.co/matches/example/video.mp4","https://c.veocdn.com/a.m3u8","blob:https://app.veo.co/id","http://c.veocdn.com/a.mp4","https://c.veocdn.com/a.jpg?file=video.mp4"]:
            with self.subTest(value=value),self.assertRaises(ValueError):match_video_link(self.report,value)
    def test_preserves_report_path_query_and_fragment(self):
        report="https://app.veo.co/matches/example/report/?source=foo#attacking"
        self.assertEqual(match_video_link(report,self.raw)["source"]["report_url"],report)
    def test_rejects_unrelated_report_and_embedded_credentials(self):
        for report in ["https://app.veo.co.evil.test/matches/example/","https://app.veo.co/clubs/example/","https://user:pass@app.veo.co/matches/example/"]:
            with self.assertRaises(ValueError):match_video_link(report,self.raw)
        with self.assertRaises(ValueError):match_video_link(self.report,"https://user:pass@c.veocdn.com/a.mp4")
    def test_does_not_mutate_an_event_link(self):
        event=self.raw+"#t=10"
        match_video_link(self.report,event)
        self.assertEqual(event,self.raw+"#t=10")

if __name__=="__main__":unittest.main()
