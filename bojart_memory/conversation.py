"""Bounded conversation context; originals remain in agent_episodes.

A current source is not proof that a generated answer is true. Historical
answers are always labelled unverified and never become reference facts.
"""
import json

from .core import canonical, digest, file_sha

SCHEMA = 'bojart.conversation-context.v1'
MAX_HISTORY_CHARS = 6000


def _answer_status(memory, context, project, current_facts, checked):
    if (not isinstance(context, dict)
            or context.get('schema') != 'bojart.agent-context.v2'
            or context.get('project') != project
            or not isinstance(context.get('text'), str)
            or digest(context['text'].encode('utf-8')) != context.get('sha256')):
        return 'withheld_unverifiable_context'
    evidence, facts = context.get('evidence'), context.get('reference_facts')
    if not isinstance(evidence, list) or not isinstance(facts, list):
        return 'withheld_unverifiable_context'
    if not evidence and not facts:
        return 'withheld_no_evidence'
    for item in evidence:
        if (not isinstance(item, dict) or item.get('project') != project
                or any(not isinstance(item.get(key), str)
                       for key in ('version_id', 'source_path', 'sha256'))):
            return 'withheld_unverifiable_context'
        row = memory.db.execute('''SELECT s.current_version,s.source_path,v.sha256
            FROM versions v JOIN sources s ON s.source_id=v.source_id
            WHERE v.version_id=? AND s.project=?''',
            (item.get('version_id'), project)).fetchone()
        if (row is None or row['current_version'] != item.get('version_id')
                or row['source_path'] != item.get('source_path')
                or row['sha256'] != item.get('sha256')):
            return 'withheld_sources_changed'
        sha = row['sha256']
        if sha not in checked:
            path = memory._object(sha)
            try:
                checked[sha] = path.is_file() and not path.is_symlink() and file_sha(path) == sha
            except OSError:
                checked[sha] = False
        if not checked[sha]:
            return 'withheld_sources_unavailable'
    for fact in facts:
        if (not isinstance(fact, dict) or not isinstance(fact.get('id'), str)
                or fact.get('project') != project
                or canonical(current_facts.get(fact['id'])) != canonical(fact)):
            return 'withheld_facts_changed'
    return 'unverified_sources_current'


def select_exchanges(memory, *, session, project, facts, limit=6):
    """Read the latest exchanges in the caller's committed SQLite snapshot."""
    current_facts = {fact['id']: fact for fact in facts}
    rows = memory.db.execute('''SELECT id,created_at,payload FROM agent_episodes
        WHERE session=? AND project=? ORDER BY created_at DESC,rowid DESC LIMIT ?''',
        (session, project, limit)).fetchall()
    selected, checked = [], {}
    for row in reversed(rows):
        try:
            payload = json.loads(row['payload'])
        except (ValueError, TypeError):
            continue
        if not isinstance(payload, dict):
            continue
        question, response = payload.get('question'), payload.get('response')
        if (not isinstance(question, str) or not 0 < len(question) <= 2000
                or not isinstance(response, dict) or not isinstance(response.get('answer'), str)):
            continue
        status = _answer_status(memory, payload.get('context'), project, current_facts, checked)
        exchange = {'event_id': row['id'], 'created_at': row['created_at'],
                    'question': question, 'answer_status': status}
        if status == 'unverified_sources_current':
            exchange['answer'] = response['answer']
        selected.append(exchange)
    return selected


def bounded_history(exchanges, max_chars=MAX_HISTORY_CHARS):
    """Keep complete fields and newest exchanges; never slice serialized JSON."""
    if type(max_chars) is not int or not 500 <= max_chars <= MAX_HISTORY_CHARS:
        raise ValueError('Budget historique hors limites.')
    exchanges = list(exchanges)
    packet = {'schema': SCHEMA, 'trusted_instructions': False,
              'answers_automatically_verified': False, 'exchanges': [],
              'omitted_exchanges': len(exchanges),
              'budget_unit': 'unicode_characters_of_serialized_json',
              'max_characters': max_chars}
    for original in reversed(exchanges):
        exchange = dict(original)
        candidate = {**packet, 'exchanges': [exchange] + packet['exchanges'],
                     'omitted_exchanges': packet['omitted_exchanges'] - 1}
        if len(canonical(candidate)) > max_chars and 'answer' in exchange:
            exchange.pop('answer')
            exchange['answer_status'] = 'withheld_budget'
        candidate = {**packet, 'exchanges': [exchange] + packet['exchanges'],
                     'omitted_exchanges': packet['omitted_exchanges'] - 1}
        if len(canonical(candidate)) > max_chars:
            break
        packet = candidate
    return packet


def encoded_history(packet=None):
    """Encode only a bounded packet produced for this conversation."""
    if packet is None:
        packet = bounded_history([])
    if (not isinstance(packet, dict) or packet.get('schema') != SCHEMA
            or packet.get('trusted_instructions') is not False
            or packet.get('answers_automatically_verified') is not False
            or not isinstance(packet.get('exchanges'), list)):
        raise ValueError('Contexte conversationnel invalide.')
    text = canonical(packet)
    budget = packet.get('max_characters')
    if type(budget) is not int or not 500 <= budget <= MAX_HISTORY_CHARS or len(text) > budget:
        raise ValueError('Contexte conversationnel hors limites.')
    return text
