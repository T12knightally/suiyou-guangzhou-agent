import json, time, unittest, uuid
from unittest.mock import patch
from agent.core import Agent, minute
from agent.providers import Provider, ProviderError
from agent.requirements import checked_updates
from agent.venue_facts import apply_facts
from tests.test_agent import BASE, TEST_TMP


class Repairs(unittest.TestCase):
    def agent(self, **changes):
        return Agent({**BASE, **changes}, TEST_TMP / uuid.uuid4().hex)

    def fact(self, day, today='2026-10-14'):
        return apply_facts(dict(id='gd_museum', ticket=None, open_minutes=None, closed=False, notice=''), day, today)

    def test_official_monday_closed(self):
        self.assertTrue(self.fact('2026-10-19')['closed'])
        self.assertEqual(self.fact('2026-10-17')['ticket'], 0)

    def test_library_wednesday_closed(self):
        p=apply_facts(dict(id='gz_library',notice=''), '2026-10-14','2026-10-14')
        self.assertTrue(p['closed'])

    def test_expired_facts_are_not_current(self):
        p=self.fact('2026-10-25','2026-10-25')
        self.assertIsNone(p['ticket']); self.assertIsNone(p['open_minutes'])
        self.assertEqual(p['facts_status'],'expired')

    def test_outside_audited_calendar_unknown(self):
        self.assertIsNone(self.fact('2026-10-24')['open_minutes'])

    def test_last_entry_boundary(self):
        a=self.agent(start='15:00'); a.origin=(113.3,23.1)
        p={**self.fact('2026-10-17'), 'name':'广东省博物馆','visit_minutes':30,'indoor':True}
        route=dict(minutes=60, walk_minutes=1, summary='测试路线', source='fixture')
        self.assertIsNone(a.schedule([p],[route,route]))
        route['minutes']=59
        self.assertIsNotNone(a.schedule([p],[route,route]))

    def test_walking_uses_road_response(self):
        p=Provider('live')
        response={'route':{'paths':[{'duration':'601','distance':'700','steps':[{'instruction':'沿路步行'}]}]}}
        with patch.object(p,'amap',return_value=response) as api:
            r=p.route((113.32,23.11),(113.321,23.111),'2026-10-17')
        self.assertEqual(api.call_args.args[0],'v3/direction/walking')
        self.assertEqual((r['minutes'],r['walk_minutes'],r['distance_m'],r['fare']),(14,11,700,0))

    def test_walking_failure_falls_back_to_transit(self):
        p=Provider('live')
        response={'route':{'transits':[{'duration':'600','walking_distance':'130','cost':'2'}]}}
        with patch.object(p,'amap',side_effect=[ProviderError('fixture'),response]) as api:
            r=p.route((113.32,23.11),(113.321,23.111),'2026-10-17')
        self.assertEqual(api.call_args.args[0],'v3/direction/transit/integrated')
        self.assertEqual(r['minutes'],25)

    def test_missing_walking_distance_fails_closed(self):
        p=Provider('live')
        with patch.object(p,'amap',return_value={'route':{'paths':[{'duration':'120'}]}}):
            with self.assertRaises(ProviderError):p.walking_route((0,0),(0,0))

    def test_exclusions_must_visit_and_stop_limit(self):
        r=self.agent(exclude_place_ids=['gd_museum'],must_visit_ids=['gz_library'],max_stops=1).run()
        for p in [r['plan'],r['rain_backup']]:
            self.assertEqual([x['id'] for x in p['places']],['gz_library'])

    def test_impossible_must_visit_not_silently_dropped(self):
        r=self.agent(scenario='closure',must_visit_ids=['gd_museum']).run()
        self.assertEqual(r['status'],'no_feasible_plan')

    def test_budget_and_time_independent_recalculation(self):
        r=self.agent().run()
        for p in [r['plan'],r['rain_backup']]:
            expected=sum(v['ticket'] for v in p['places'])+sum(v['fare'] for v in p['routes'])+35+15
            self.assertEqual(p['cost']['per_person'],expected); self.assertLessEqual(expected,BASE['budget'])
            previous=minute(BASE['start'])
            for e in p['schedule']['entries']:
                self.assertEqual(minute(e['start']),previous)
                self.assertGreater(minute(e['end']),previous);previous=minute(e['end'])
            self.assertLessEqual(previous,minute(BASE['end']))
            self.assertEqual(len(p['routes']),len(p['places'])+1)

    def extract(self, field, value, quote, message=None):
        return checked_updates({'updates':{field:value},'evidence':{field:quote},'questions':[]},message or quote,'2026-10-14')

    def test_forged_quotes_and_values_rejected(self):
        for args in [('budget',500,'每人500元','每人80元'),('budget',500,'每人80元',None),('date','2026-10-18','周六',None)]:
            accepted,questions=self.extract(*args);self.assertFalse(accepted);self.assertTrue(questions)

    def test_ambiguous_budget_asks(self):
        self.assertFalse(self.extract('budget',100,'预算100元')[0])
        self.assertFalse(self.extract('budget',100,'两人总预算100元')[0])
        self.assertEqual(self.extract('budget',100,'每人100元')[0],{'budget':100})

    def test_dates_and_evening_time_grounded(self):
        self.assertEqual(self.extract('date','2026-10-17','周六')[0],{'date':'2026-10-17'})
        self.assertEqual(self.extract('end','20:00','晚上八点')[0],{'end':'20:00'})

    def test_forged_preference_and_forbidden_field(self):
        self.assertFalse(self.extract('exclude_place_ids',['gd_museum'],'不去广州图书馆')[0])
        with self.assertRaises(ValueError):self.extract('api_key','invented','invented')

    def test_deadline_stops_tools_but_saves_result(self):
        a=self.agent();a.deadline=time.monotonic()-1
        r=a.run();self.assertEqual(r['status'],'unavailable')
        self.assertTrue((a.save_dir/(r['run_id']+'.json')).exists())

    def test_model_can_reselect_after_no_feasible_plan(self):
        def response(name,args):return {'choices':[{'message':{'role':'assistant','tool_calls':[{'id':uuid.uuid4().hex,'type':'function','function':{'name':name,'arguments':json.dumps(args)}}]}}]}
        replies=[response('query_weather',{}),response('query_places',{}),response('build_plan',{'candidate_ids':['gd_museum']}),response('build_plan',{'candidate_ids':['gz_library']})]
        with patch.dict('os.environ',{'LLM_API_KEY':'test','LLM_MODEL':'test','LLM_BASE_URL':'https://example.invalid/v1'}),patch('agent.core.fetch_json',side_effect=replies):
            r=self.agent(engine='llm',scenario='closure').run()
        self.assertEqual(r['status'],'draft');self.assertEqual(r['usage']['model_calls'],4)
        self.assertEqual(r['plan']['places'][0]['id'],'gz_library')

    def test_model_cannot_submit_more_than_three_candidates(self):
        def response(name,args):return {'choices':[{'message':{'role':'assistant','tool_calls':[{'id':uuid.uuid4().hex,'type':'function','function':{'name':name,'arguments':json.dumps(args)}}]}}]}
        replies=[response('query_weather',{}),response('query_places',{}),response('build_plan',{'candidate_ids':['gd_museum','gz_library','opera','huacheng']}),response('build_plan',{'candidate_ids':['gz_library']})]
        with patch.dict('os.environ',{'LLM_API_KEY':'test','LLM_MODEL':'test','LLM_BASE_URL':'https://example.invalid/v1'}),patch('agent.core.fetch_json',side_effect=replies) as model:
            r=self.agent(engine='llm').run()
        self.assertEqual(r['status'],'draft');self.assertEqual(r['usage']['model_calls'],4)
        observations=[m['content'] for m in model.call_args.kwargs['payload']['messages'] if m['role']=='tool']
        self.assertTrue(any('1到3个不同候选' in x for x in observations))


if __name__=='__main__':unittest.main()
