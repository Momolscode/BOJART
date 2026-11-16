"""Bounded local inference settings. No automatic hardware or speed claim."""

DEFAULTS = {'num_ctx': 32768, 'num_predict': 768, 'think': False,
            'keep_alive': 300}


def chat_settings(value=None):
    if value is None:
        value = {}
    if not isinstance(value, dict) or set(value) - set(DEFAULTS):
        raise ValueError('Réglages de conversation invalides.')
    result = {**DEFAULTS, **value}
    for name, low, high in [('num_ctx', 8192, 65536), ('num_predict', 128, 2048),
                            ('keep_alive', 0, 1800)]:
        if type(result[name]) is not int or not low <= result[name] <= high:
            raise ValueError('Réglage de conversation hors limites : ' + name)
    if type(result['think']) is not bool:
        raise ValueError('think doit être un booléen.')
    return result


def prompt_budget(messages, settings):
    # Conservative byte envelope, NOT an exact tokenizer or proof that a server
    # honors num_ctx. Reserve space for the chat template and generated answer.
    used = sum(len(m['content'].encode('utf-8')) for m in messages)
    available = settings['num_ctx'] - settings['num_predict'] - 512
    if used > available:
        raise ValueError('Contexte trop volumineux pour ce profil ; réduire le contexte ou augmenter num_ctx.')
    return {'utf8_content_bytes': used, 'conservative_envelope': available,
            'exact_token_count': False}


def measurements(response, elapsed):
    values = {}
    for name in ('total_duration', 'load_duration', 'prompt_eval_duration',
                 'eval_duration', 'prompt_eval_count', 'eval_count'):
        value = response.get(name)
        if type(value) is int and value >= 0:
            values[name] = value
    duration = values.get('eval_duration', 0)
    count = values.get('eval_count', 0)
    return {'wall_ms': round(elapsed * 1000, 2), 'provider': values,
            'generated_tokens_per_second': round(count * 1e9 / duration, 2) if duration else None,
            'first_token_ms': None, 'streamed_to_interface': False}
