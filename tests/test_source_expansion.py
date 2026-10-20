import unittest
from unittest.mock import patch
from agent.providers import Provider
from agent.venue_facts import apply_facts

class SourceExpansion(unittest.TestCase):
    def fact(self,pid,today='2026-10-14'):
        return apply_facts(dict(id=pid,ticket=None,open_minutes=None,closed=False,notice=''), '2026-10-17',today)

    def test_description_is_not_operating_evidence(self):
        p=self.fact('chen')
        self.assertIsNone(p['ticket']);self.assertIsNone(p['open_minutes'])
        self.assertEqual(p['facts_status'],'official_description_only')

    def test_partial_closure_keeps_other_areas_open(self):
        p=self.fact('nanyue')
        self.assertFalse(p['closed'])
        self.assertIn('东门暂停',p['current_notice'])
        self.assertIn('西门',p['entry_note'])
        self.assertEqual(p['ticket'],0)
        self.assertNotIn('南越宫苑馆',p['visit_scope'].split('；')[0])

    def test_free_guidance_does_not_imply_free_admission(self):
        p=self.fact('peasant')
        self.assertIsNone(p['ticket']);self.assertFalse(p['reservation_required'])
        self.assertEqual(p['last_entry_minute'],1020)

    def test_expired_notice_cannot_override_map(self):
        p=self.fact('nanyue','2026-10-30')
        self.assertIsNone(p['ticket']);self.assertNotIn('poi_query',p)

    def query_nanyue(self,rows):
        p=Provider('live');p.day='2026-10-17';p.preferred_ids=['nanyue']
        with patch('agent.providers.now',return_value='2026-10-14T10:00:00+08:00'),patch.object(p,'amap',return_value={'pois':rows}):
            return next(v for v in p.places([],False) if v['id']=='nanyue')

    def test_wrong_gate_not_silently_used(self):
        p=self.query_nanyue([dict(name='南越王博物院(王宫展区)',adcode='440104',location='113.27,23.13')])
        self.assertTrue(p['closed']);self.assertIn('不代表全馆闭馆',p['notice'])

    def test_approved_entry_poi_used_for_route(self):
        p=self.query_nanyue([dict(name='广州南越王宫博物馆(出口)',adcode='440104',location='113.269318,23.127815',address='北京路')])
        self.assertFalse(p['closed']);self.assertEqual((p['lon'],p['lat']),(113.269318,23.127815))
        self.assertEqual(p['coordinate_status'],'amap_exact_name')
