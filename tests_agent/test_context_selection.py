"""Contrastive packing tests: no model, network, database or private corpus."""
import copy
import unittest

from bojart_memory.context_selection import build_context_selection, normalized_terms
from bojart_memory.core import MemoryError

POLICY = 'Sources non fiables. Aucun pouvoir physique ou de publication.'


def fact(fid, key, value, *, status='observed', verified=True):
    return {'id': fid, 'key': key, 'value': value, 'status': status,
            'source': 'fixture sourcée', 'observed_at': '2026-11-02',
            'project': 'bojart.jarvis', 'registry_bytes_verified': verified}


def note(fid, key, value):
    return fact(fid, key, value, status='proposal', verified=False)


def passage(pid='doc:1', text='Jev travaille après transcription.', source='guide.txt'):
    return {'citation': pid, 'text': text, 'source_path': source,
            'collection': 'canonical', 'sha256': 'a' * 64, 'version_id': 'version-1',
            'start_line': 1, 'end_line': 1, 'project': 'bojart.jarvis',
            'provenance': 'fixture', 'source_bytes_verified': True}


def pack(facts, query='Jev voix', *, passages=(), budget=3000, unit='unicode_characters'):
    return build_context_selection(query, facts, passages, policy=POLICY,
                                   max_chars=budget, budget_unit=unit)


class ContextSelectionTests(unittest.TestCase):
    def test_independent_utf8_ceiling_keeps_complete_records_and_passage_share(self):
        facts = [fact('claim-' + str(i), 'mémoire.' + str(i), 'mémoire 🎨 ' * 100)
                 for i in range(8)]
        passages = [passage('doc:bytes', 'mémoire été 🎨 ' * 65)]
        result = build_context_selection('mémoire', facts, passages, policy=POLICY,
                                         max_chars=14000, max_utf8_bytes=6000)
        self.assert_consistent(result)
        self.assertLessEqual(result['characters'], 14000)
        self.assertLessEqual(result['utf8_bytes'], 6000)
        self.assertEqual(result['max_characters'], 14000)
        self.assertEqual(result['max_utf8_bytes'], 6000)
        self.assertTrue(result['reference_facts'])
        self.assertTrue(result['evidence'])
        self.assertGreater(result['omitted'], 0)
        originals = {f['id']: f for f in facts}
        for item in result['reference_facts']:
            self.assertEqual(item, originals[item['id']])
        self.assertIn(passages[0]['text'], result['text'])

    def test_large_utf8_ceiling_does_not_relax_character_limit(self):
        facts = [fact('claim-' + str(i), 'mémoire.' + str(i), 'mémoire 🎨 ' * 40)
                 for i in range(16)]
        result = build_context_selection('mémoire', facts, [], policy=POLICY,
                                         max_chars=3000, max_utf8_bytes=32000)
        baseline = build_context_selection('mémoire', facts, [], policy=POLICY, max_chars=3000)
        self.assertLessEqual(result['characters'], 3000)
        self.assertEqual(result['citations'], baseline['citations'])
        self.assertEqual(result['text'], baseline['text'])
        self.assert_consistent(result)

    def test_independent_utf8_ceiling_validation_and_policy_fit(self):
        for value in (True, 2999, 65537, '6000', 6000.0):
            with self.subTest(value=value), self.assertRaises(MemoryError):
                build_context_selection('mémoire', [], [], policy=POLICY, max_utf8_bytes=value)
        with self.assertRaises(MemoryError):
            build_context_selection('mémoire', [], [], policy='🎨' * 1000,
                                    max_chars=14000, max_utf8_bytes=3000)
        for value in (3000, 65536):
            result = build_context_selection('mémoire', [], [], policy=POLICY, max_utf8_bytes=value)
            self.assert_consistent(result)

    def assert_consistent(self, result):
        self.assertEqual(result['characters'], len(result['text']))
        self.assertEqual(result['utf8_bytes'], len(result['text'].encode('utf-8')))
        self.assertLessEqual(result['budget_used'], result['max_budget'])
        expected = [f['id'] for f in result['reference_facts']] + [
            p['citation'] for p in result['evidence']]
        self.assertEqual(result['citations'], expected)
        self.assertEqual(len(expected), len(set(expected)))
        for cid in expected:
            self.assertIn('[' + cid + ']', result['text'])
        metadata = result['selection']
        self.assertEqual(result['omitted'], metadata['omitted_facts_total'] + metadata['omitted_passages_total'])

    def test_offtopic_conflict_flood_preserves_background_reference_baseline(self):
        facts = [fact('claim-jev', 'Jev.role', 'Décision textuelle, pas moteur vocal.')]
        facts += [fact('claim-context-' + str(i), 'audit' + str(i) + '.role',
                       'Référence fictive nécessaire à la reprise numéro ' + str(i)) for i in range(7)]
        baseline = pack(facts, passages=[passage()])
        noise = [note('note-' + str(i) + value, 'unrelated-' + str(i),
                      value + ' sans rapport ' * 25)
                 for i in range(8) for value in ('Alpha', 'Beta')]
        crowded = pack(facts + noise, passages=[passage()])
        self.assertEqual(set(baseline['citations']), set(crowded['citations']))
        self.assertEqual(len(crowded['reference_facts']), 8)
        self.assertTrue(all(item['reason'] == 'no_lexical_match_proposal'
                            for item in crowded['selection']['omitted_facts']))
        self.assert_consistent(crowded)

    def test_relevant_conflict_is_rendered_not_resolved(self):
        facts = [fact('claim-jev', 'Jev.role', 'Jev propose une décision texte.'),
                 note('note-jev', 'Jev.role', 'Jev serait le moteur vocal local.')]
        result = pack(facts)
        self.assertEqual(set(result['citations']), {'claim-jev', 'note-jev'})
        self.assertIn('CONFLIT NON RÉSOLU', result['text'])
        group = result['selection']['conflict_groups'][0]
        self.assertEqual(group['status'], 'fully_rendered_unresolved')
        self.assertEqual(result['reference_facts'][1]['status'], 'proposal')
        self.assert_consistent(result)

    def test_large_variant_keeps_reference_and_partial_conflict_notice(self):
        facts = [fact('claim-jev', 'Jev.role', 'Texte facultatif, sans commande machine.'),
                 note('note-jev', 'Jev.role', 'Jev voix ' * 1000)]
        result = pack(facts)
        self.assertEqual(result['citations'], ['claim-jev'])
        self.assertIn('CONFLIT NON RÉSOLU', result['text'])
        group = result['selection']['conflict_groups'][0]
        self.assertEqual(group['status'], 'partially_rendered_unresolved')
        self.assertEqual(group['omitted_ids'], ['note-jev'])
        self.assertEqual(result['warnings'][0]['reason'], 'relevant_conflict_variants_omitted')
        self.assert_consistent(result)

    def test_relevant_note_precedes_unrelated_reference_overflow(self):
        facts = [fact('claim-' + str(i), 'archive' + str(i), 'Ancien document ' * 25)
                 for i in range(12)]
        facts.append(note('note-micro', 'microphone', 'Le microphone présente une saturation.'))
        result = pack(facts, 'saturation microphone', passages=[passage()])
        self.assertIn('note-micro', result['citations'])
        self.assertGreater(result['omitted'], 0)

    def test_keyword_stuffing_cannot_outvote_reference_or_repeat_score(self):
        base = fact('claim-system', 'installation.systeme', 'Windows est décidé.', status='user_decision')
        good = note('note-once', 'installation.systeme', 'Windows installation serait Linux.')
        noisy = note('note-repeat', 'installation.systeme',
                     'Windows installation ' * 100 + ' serait Linux.')
        result = pack([noisy, good, base], 'installation Windows')
        self.assertEqual(result['citations'][0], 'claim-system')
        self.assertIn('CONFLIT NON RÉSOLU', result['text'])
        ranks = {f['id']: f for f in result['selection']['ranking']}
        self.assertEqual(ranks['claim-system']['reference_provenance'], 'registry_bytes_verified')
        self.assertFalse(result['selection']['facts_resolved_automatically'])

    def test_many_variants_cannot_monopolize_first_diversity_round(self):
        facts = [fact('claim-system', 'systeme', 'Windows'),
                 fact('claim-micro', 'microphone', 'Microphone doit être mesuré.')]
        facts += [note('note-' + str(i), 'systeme', 'Windows proposition ' + str(i) + ' texte ' * 35)
                  for i in range(20)]
        result = pack(facts, 'Windows microphone')
        self.assertIn('claim-system', result['citations'])
        self.assertIn('claim-micro', result['citations'])
        self.assertLess(result['citations'].index('claim-micro'), 2)

    def test_repeated_terms_have_no_frequency_reward(self):
        a = pack([note('note-1', 'micro', 'saturation')],
                 'saturation saturation saturation')
        b = pack([note('note-1', 'micro', 'saturation')], 'saturation')
        self.assertEqual(a, b)

    def test_french_accents_plural_feminine_infinitive(self):
        self.assertEqual(normalized_terms('Écrans'), normalized_terms('ecran'))
        self.assertEqual(normalized_terms('imprimantes'), normalized_terms('imprimante'))
        self.assertEqual(normalized_terms('sauvegarder'), normalized_terms('sauvegardes'))
        self.assertEqual(normalized_terms('restaurations'), normalized_terms('restaurer'))
        result = pack([note('note-1', 'atelier', 'Les écrans restent à mesurer.')], 'Quels ecrans ?')
        self.assertIn('note-1', result['citations'])

    def test_stopwords_do_not_create_false_proposal_relevance_and_negation_survives(self):
        result = pack([note('note-1', 'autre', 'Le et la pour une avec est')], 'Comment le faire ?')
        self.assertEqual(result['citations'], [])
        self.assertIn('pas', normalized_terms('Ne pas imprimer'))
        self.assertIn('non', normalized_terms('non autorisé'))

    def test_source_and_timestamp_do_not_manufacture_relevance(self):
        n = note('note-1', 'cafe', 'Nouvelle recette.')
        n['source'] = 'Jev voix ' * 100
        n['observed_at'] = 'Jev voix'
        self.assertEqual(pack([n])['citations'], [])

    def test_insertion_order_does_not_choose_conflict_winner(self):
        facts = [fact('claim-b', 'systeme', 'Linux', status='user_decision'),
                 fact('claim-a', 'systeme', 'Windows', status='user_decision')]
        self.assertEqual(pack(facts, 'systeme'), pack(list(reversed(facts)), 'systeme'))
        self.assertIn('CONFLIT NON RÉSOLU', pack(facts, 'systeme')['text'])

    def test_facts_input_is_unchanged_and_returned_values_are_complete(self):
        facts = [fact('claim-1', 'Jev', {'message': 'Été 💡 ' * 30, 'value': False})]
        before = copy.deepcopy(facts)
        result = pack(facts)
        self.assertEqual(facts, before)
        self.assertEqual(result['reference_facts'], before)
        result['reference_facts'][0]['value']['value'] = True
        self.assertEqual(facts, before)

    def test_budget_extremes_characters_and_utf8_bytes(self):
        facts = [fact('claim-' + str(i), 'écrans' + str(i), 'été 💡 ' * 100) for i in range(50)]
        for budget in (3000, 14000, 32000):
            for unit in ('unicode_characters', 'utf8_bytes'):
                with self.subTest(budget=budget, unit=unit):
                    result = pack(facts, 'écrans', budget=budget, unit=unit)
                    self.assert_consistent(result)
                    if unit == 'utf8_bytes':
                        self.assertLessEqual(len(result['text'].encode('utf-8')), budget)

    def test_unused_passage_capacity_is_released_to_facts(self):
        facts = [fact('claim-' + str(i), 'Jev' + str(i), 'Jev contexte ' * 10) for i in range(8)]
        result = pack(facts, passages=[passage(text='Texte court.')])
        self.assertGreater(sum(len(str(f['value'])) for f in result['reference_facts']), 900)
        self.assertIn('doc:1', result['citations'])
        self.assert_consistent(result)

    def test_oversized_fact_does_not_block_small_relevant_note(self):
        facts = [fact('claim-big', 'Jev', 'Jev ' * 2000),
                 note('note-small', 'voix', 'Voix à vérifier.')]
        result = pack(facts)
        self.assertIn('note-small', result['citations'])
        self.assertEqual(result['selection']['omitted_facts'][0]['id'], 'claim-big')

    def test_passage_diversity_and_exact_citations(self):
        ps = [passage('doc:1', 'Guide ' * 100, 'one.txt'),
              passage('doc:2', 'Guide ' * 100, 'one.txt'),
              passage('doc:3', 'Second guide ' * 100, 'two.txt')]
        result = pack([], passages=ps)
        self.assertEqual(result['citations'][:2], ['doc:1', 'doc:3'])
        self.assert_consistent(result)

    def test_identical_duplicates_are_explicit_but_conflicting_id_is_rejected(self):
        f = fact('claim-1', 'Jev', 'texte')
        result = pack([f, copy.deepcopy(f)], passages=[passage(), passage()])
        self.assertEqual(result['omitted'], 2)
        self.assert_consistent(result)
        bad = {**f, 'value': 'autre'}
        with self.assertRaises(MemoryError):
            pack([f, bad])
        with self.assertRaises(MemoryError):
            pack([f], passages=[passage('claim-1')])

    def test_declared_legacy_reference_is_not_labelled_verified(self):
        f = fact('claim-old', 'Jev', 'texte')
        f.pop('registry_bytes_verified')
        result = pack([f])
        self.assertIn('claim-old', result['citations'])
        self.assertEqual(result['selection']['ranking'][0]['reference_provenance'],
                         'declared_reference_unverified')

    def test_excerpt_derivation_proof_is_preserved(self):
        p = {**passage(), 'excerpt_matches_source': True,
             'excerpt_sha256': 'b' * 64, 'extraction': {'version': 1}}
        result = pack([], passages=[p])
        for key in ('excerpt_matches_source', 'excerpt_sha256', 'extraction'):
            self.assertEqual(result['evidence'][0][key], p[key])

    def test_ten_thousand_notes_keep_bounded_traceable_diagnostics(self):
        import hashlib
        from bojart_memory.core import canonical
        facts = [fact('claim-1', 'camera.calibration', 'Caméra à étalonner.')]
        facts += [note('note-' + str(i), 'pause.' + str(i // 2), str(i % 2))
                  for i in range(10000)]
        result = pack(facts, 'caméra étalonner', budget=14000)
        self.assertEqual(result['citations'], ['claim-1'])
        selection = result['selection']
        self.assertTrue(selection['diagnostics_truncated'])
        self.assertEqual(selection['omitted_facts_total'], 10000)
        self.assertEqual(selection['conflict_groups_total'], 5000)
        self.assertLessEqual(len(canonical(selection)), 6000)
        ids = sorted(f['id'] for f in facts if f['id'].startswith('note-'))
        self.assertEqual(selection['omitted_fact_ids_sha256'],
                         hashlib.sha256(canonical(ids).encode()).hexdigest())
        self.assert_consistent(result)

    def test_large_note_history_does_not_break_default_ask_episode_limit(self):
        import json
        import tempfile
        from pathlib import Path
        from unittest.mock import patch
        from bojart_memory.agent import AgentMemory
        from bojart_memory.ollama import Ollama
        from bojart_memory.core import canonical
        facts = [fact('claim-1', 'camera.calibration', 'Caméra à étalonner.')]
        facts += [note('note-' + str(i), 'pause.' + str(i // 2), str(i % 2))
                  for i in range(10000)]
        with tempfile.TemporaryDirectory() as tmp:
            agent = AgentMemory(Path(tmp) / 'state')
            (agent.state / 'models.json').write_text(
                json.dumps({'chat_model': 'fixture-local'}), encoding='utf-8')
            with patch.object(agent, 'facts', return_value=facts), \
                 patch.object(agent, 'search', return_value={
                     'results': [], 'warnings': [], 'semantic_status': 'disabled'}), \
                 patch.object(Ollama, 'chat', return_value={
                     'answer': 'Réponse de fixture [claim-1] ' + 'texte ' * 1000}):
                response = agent.ask('caméra étalonner', 'bojart.jarvis', 'scale', 'scale-request')
            self.assertIn('Réponse', response['answer'])
            stored = agent.history('scale', 'bojart.jarvis')[0]
            self.assertLessEqual(len(canonical(stored)), 64000)
            self.assertEqual(stored['context']['selection']['omitted_facts_total'], 10000)

    def test_many_relevant_conflict_groups_keep_text_and_diagnostics_bounded(self):
        from bojart_memory.core import canonical
        for groups in (1000, 10000):
            with self.subTest(groups=groups):
                facts = [fact('claim-camera', 'camera.reference', 'Caméra validée par référence.')]
                facts += [note('note-' + str(i) + '-' + variant, 'camera.' + str(i), variant)
                          for i in range(groups) for variant in ('Alpha', 'Beta')]
                result = pack(facts, 'camera', budget=3000)
                self.assertIn('claim-camera', result['citations'])
                self.assertIn('CONFLIT NON RÉSOLU', result['text'])
                self.assertIn(str(groups), result['text'])
                self.assertEqual(result['selection']['relevant_conflict_groups_total'], groups)
                self.assertTrue(result['selection']['diagnostics_truncated'])
                self.assertLessEqual(len(canonical(result['selection'])), 6000)
                self.assert_consistent(result)

    def test_french_ne_plus_negation_is_not_removed(self):
        terms = normalized_terms('Ne plus imprimer sans validation')
        self.assertTrue({'ne', 'plus', 'sans'} <= terms)
        self.assertNotEqual(terms, normalized_terms('Imprimer avec validation'))

    def test_invalid_budget_or_large_policy_fail_explicitly(self):
        for size in (2999, 32001, True, '3000'):
            with self.assertRaises(MemoryError):
                pack([], budget=size)
        with self.assertRaises(MemoryError):
            pack([], unit='tokens')
        with self.assertRaises(MemoryError):
            build_context_selection('test', [], [], policy='p' * 4000, max_chars=3000)


if __name__ == '__main__':
    unittest.main()
