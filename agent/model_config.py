"""Server-side provider selection; credentials never enter user-visible state."""
import os
from .providers import ProviderError

ENV_FIELDS={'AMAP_KEY','LLM_API_KEY','LLM_MODEL','LLM_BASE_URL','LLM_PROVIDER',
            'DEEPSEEK_API_KEY','DEEPSEEK_MODEL','DEEPSEEK_BASE_URL'}

def model_config(choice='default'):
    if choice not in ('default','deepseek'): raise ProviderError('未知模型选项')
    if choice=='deepseek':
        provider='deepseek'; key=os.getenv('DEEPSEEK_API_KEY','')
        model=os.getenv('DEEPSEEK_MODEL','deepseek-flash')
        base=os.getenv('DEEPSEEK_BASE_URL','https://api.deepseek.com')
    else:
        provider=os.getenv('LLM_PROVIDER','compatible'); key=os.getenv('LLM_API_KEY','')
        model=os.getenv('LLM_MODEL',''); base=os.getenv('LLM_BASE_URL','')
    if not key or not model or not base.startswith('https://'):
        raise ProviderError('请在服务端配置所选模型的 API Key、模型名和 HTTPS Base URL')
    extra={'enable_thinking':False} if provider=='qwen' else ({'thinking':{'type':'disabled'}} if provider=='deepseek' else {})
    return dict(provider=provider,key=key,model=model,base=base.rstrip('/'),extra=extra)

def redact(value):
    """Remove configured credentials even if an external service echoes one."""
    secrets=[os.getenv(k,'') for k in ENV_FIELDS if k.endswith('KEY')]
    if isinstance(value,str):
        for secret in secrets:
            if secret: value=value.replace(secret,'[REDACTED]')
        return value
    if isinstance(value,dict): return {str(k):redact(v) for k,v in value.items()}
    if isinstance(value,(list,tuple)): return [redact(v) for v in value]
    return value
