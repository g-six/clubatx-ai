import copy
import unittest
from report_player_names import personalize_reports, JERSEY

class ReportNameTests(unittest.TestCase):
    def setUp(self):
        self.reports = [{'id':'overview','team':'PF','blocks':[{'type':'bullet','text':'#19 scored, assisted by No. 10; their #10 replied. 3 goals in 19 minutes.'}]}]
        self.links = [{'team':'PF','jersey_number':19,'player_name':'Kyle Echiverri','athlete_slug':'kyle','lineup_id':1}, {'team':'PF','jersey_number':10,'player_name':'John Montesclaros','athlete_slug':'john','lineup_id':2}]
        self.mentions = [{'report_id':'overview','block_index':0,'occurrence':i,'team':team} for i,team in enumerate(['PF','PF','P2P'])]
    def test_names_are_team_scoped_and_source_is_preserved(self):
        before=copy.deepcopy(self.reports)
        result=personalize_reports(self.reports,self.mentions,self.links)
        self.assertEqual(result[0]['blocks'][0]['text'],'Kyle Echiverri scored, assisted by John Montesclaros; their #10 replied. 3 goals in 19 minutes.')
        self.assertEqual(result[0]['source_blocks'],before[0]['blocks'])
        self.assertEqual(self.reports,before)
        self.assertEqual(len(result[0]['identity_substitutions']),2)
    def test_repeated_personalization_is_idempotent(self):
        result=personalize_reports(self.reports,self.mentions,self.links)
        self.assertEqual(personalize_reports(result,self.mentions,self.links),result)
    def test_missing_context_is_rejected(self):
        with self.assertRaisesRegex(ValueError,'team context'):
            personalize_reports(self.reports,self.mentions[:2],self.links)
    def test_unknown_mention_stays_jersey(self):
        for mention in self.mentions: mention['team']=None
        self.assertEqual(personalize_reports(self.reports,self.mentions,self.links)[0]['blocks'],self.reports[0]['blocks'])
    def test_confirmed_source_jersey_aliases_use_the_same_player(self):
        reports=[{'id':'r','blocks':[{'text':'Jersey #20 and number 21 are #28.'}]}]
        links=[{'team':'PF','jersey_number':j,'player_name':'Camilo Martinez','athlete_slug':'camilo-adrian','lineup_id':3} for j in [20,21,28]]
        mentions=[{'report_id':'r','block_index':0,'occurrence':i,'team':'PF'} for i in range(3)]
        result=personalize_reports(reports,mentions,links)
        self.assertEqual(result[0]['blocks'][0]['text'],'Camilo Martinez and Camilo Martinez are Camilo Martinez.')
        self.assertEqual(len(list(JERSEY.finditer('#190 and 28 attempts'))),0)
    def test_incomplete_or_conflicting_links_rejected(self):
        self.links[0]['lineup_id']=None
        with self.assertRaisesRegex(ValueError,'confirmed fixture'):
            personalize_reports(self.reports,self.mentions,self.links)

if __name__=='__main__':unittest.main()
