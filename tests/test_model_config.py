import io, json, os, unittest
from unittest.mock import patch
from urllib.error import HTTPError
from agent.model_config import model_config,redact
from agent.providers import fetch_json,ProviderError

class ModelConfigTests(unittest.TestCase):
    def test_qwen_non_thinking(self):
        with patch.dict(os.environ,{'LLM_PROVIDER':'qwen','LLM_API_KEY':'fake-qwen','LLM_MODEL':'qwen3.8-flash','LLM_BASE_URL':'https://example.invalid/v1'},clear=True):
            self.assertEqual(model_config()['extra'],{'enable_thinking':False})
    def test_deepseek_non_thinking(self):
        with patch.dict(os.environ,{'DEEPSEEK_API_KEY':'fake-deepseek'},clear=True):
            c=model_config('deepseek'); self.assertEqual(c['extra'],{'thinking':{'type':'disabled'}})
            self.assertEqual(c['model'],'deepseek-flash')
    def test_keys_redacted_recursively(self):
        with patch.dict(os.environ,{'AMAP_KEY':'fake-private-key'}):
            self.assertEqual(redact({'a':['echo fake-private-key']}),{'a':['echo [REDACTED]']})
    def test_auth_failure_does_not_repeat(self):
        e=HTTPError('https://example.invalid/?key=secret',401,'secret',{},io.BytesIO(b'secret'))
        with patch('agent.providers.urlopen',side_effect=e) as call:
            with self.assertRaisesRegex(ProviderError,'HTTP 401') as raised: fetch_json('https://example.invalid')
            self.assertEqual(call.call_count,1); self.assertNotIn('secret',str(raised.exception))
    def test_non_dict_response_rejected(self):
        class Response(io.BytesIO): pass
        with patch('agent.providers.urlopen',return_value=Response(b'[]')):
            with self.assertRaises(ProviderError): fetch_json('https://example.invalid',attempts=1)
