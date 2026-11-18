import copy
import unittest

from tools.validate import (RESERVED_TOPIC_IDS, TOOL_NAMES, TOPIC_CATEGORIES, WHEN, WHERE, draft_ids, topic_draft_ids,
                            validate, validate_checklists, validate_tooldata, validate_topics)


def ok(**step_over):
    step = {'id': 's1', 'text': 'Do the thing.'}
    step.update(step_over)
    return {
        'id': 'p1', 'title': 'Proto', 'category': 'life',
        'steps': [step, {'id': 's2', 'text': 'Then this.'}],
        'sources': [{'name': 'Some Source'}], 'reviewed': '2026-11-16',
    }


def advanced():
    p = ok()
    p.update({'tier': 'advanced', 'indications': ['a'], 'contraindications': ['b'],
              'equipment': ['c'], 'complications': ['d']})
    return p


def errs(protocols, figs=frozenset()):
    return validate(protocols, set(figs))[0]


class ValidateTests(unittest.TestCase):
    def test_valid_protocol_has_no_errors(self):
        self.assertEqual(validate([ok()], set()), ([], []))

    def test_notes_optional_list_of_non_blank_strings(self):
        good = ok(); good['notes'] = ['A note']
        self.assertEqual(errs([good]), [])
        for bad in ('text', [], [''], ['  '], [5], None):
            p = ok(); p['notes'] = bad
            self.assertTrue(any('notes' in e for e in errs([p])), bad)

    def test_duplicate_protocol_id(self):
        other = ok()
        self.assertTrue(any('duplicate' in e for e in errs([ok(), other])))

    def test_duplicate_step_id(self):
        p = ok()
        p['steps'][1]['id'] = 's1'
        self.assertTrue(any('duplicate' in e for e in errs([p])))

    def test_branch_target_missing(self):
        p = ok(ask={'q': 'Q?', 'yes': 'nope', 'no': 's2'})
        self.assertTrue(any('nope' in e for e in errs([p])))

    def test_branch_no_target_missing(self):
        p = ok(ask={'q': 'Q?', 'yes': 's2', 'no': 'gone'})
        self.assertTrue(any('gone' in e for e in errs([p])))

    def test_unreachable_step(self):
        p = ok(end=True)  # s1 ends, so s2 can never be reached
        self.assertTrue(any('unreachable' in e and 's2' in e for e in errs([p])))

    def test_branch_makes_step_reachable(self):
        p = ok(ask={'q': 'Q?', 'yes': 's3', 'no': 's3'})
        p['steps'].append({'id': 's3', 'text': 'Third.'})
        p['steps'][1]['end'] = True  # s2 is skipped by both branches
        self.assertTrue(any('s2' in e and 'unreachable' in e for e in errs([p])))
        p['steps'][0]['ask']['no'] = 's2'
        self.assertEqual(errs([p]), [])

    def test_missing_sources(self):
        for bad in (None, []):
            p = ok()
            if bad is None:
                del p['sources']
            else:
                p['sources'] = bad
            self.assertTrue(any('sources' in e for e in errs([p])), bad)

    def test_missing_reviewed(self):
        p = ok()
        del p['reviewed']
        self.assertTrue(any('reviewed' in e for e in errs([p])))

    def test_missing_required_fields(self):
        for field in ('id', 'title', 'category'):
            p = ok()
            del p[field]
            self.assertTrue(any(field in e for e in errs([p])), field)
        p = ok()
        del p['steps'][0]['text']
        self.assertTrue(any('text' in e for e in errs([p])))
        p = ok()
        del p['steps'][0]['id']
        self.assertTrue(any('id' in e for e in errs([p])))

    def test_unknown_fig(self):
        self.assertTrue(any('fig' in e for e in errs([ok(fig='nope')], {'other'})))
        self.assertEqual(errs([ok(fig='known')], {'known'}), [])

    def test_unknown_tool(self):
        self.assertTrue(any('tool' in e for e in errs([ok(tool='bogus')])))
        self.assertEqual(errs([ok(tool='tq')]), [])

    def test_unknown_category(self):
        p = ok()
        p['category'] = 'nope'
        self.assertTrue(any('category' in e for e in errs([p])))

    def test_advanced_requires_indications_contraindications_equipment_complications(self):
        self.assertEqual(errs([advanced()]), [])
        for field in ('indications', 'contraindications', 'equipment', 'complications'):
            p = advanced()
            del p[field]
            self.assertTrue(any(field in e for e in errs([p])), field)

    def test_reserved_protocol_ids(self):
        for rid in ('tool', 'report', 'all'):
            p = ok()
            p['id'] = rid
            self.assertTrue(any('reserved' in e for e in errs([p])), rid)

    def test_protocol_id_pattern(self):
        for bad in ('Bleeding', 'a_b', '-x', 'a b', 'x' * 61, 'a\n', 'é'):
            p = ok()
            p['id'] = bad
            self.assertTrue(any('id must be' in e for e in errs([p])), repr(bad))
        for good in ('a', '0a', 'cpr-adult', 'x' * 60):
            p = ok()
            p['id'] = good
            self.assertEqual(errs([p]), [], good)

    def test_coach_is_optional_object_of_two_positive_ints(self):
        for good in ({'compressions': 30, 'breaths': 2}, {'compressions': 15, 'breaths': 1}, {'compressions': 99, 'breaths': 99}):
            p = ok()
            p['coach'] = good
            self.assertEqual(errs([p]), [])
        for bad in (5, 'x', [], {}, {'compressions': 30}, {'compressions': 0, 'breaths': 2},
                    {'compressions': 30, 'breaths': -1}, {'compressions': 30.5, 'breaths': 2},
                    {'compressions': '30', 'breaths': 2}, {'compressions': True, 'breaths': 2}, {'compressions': 100, 'breaths': 2},
                    {'compressions': 30, 'breaths': 100}):
            p = ok()
            p['coach'] = bad
            self.assertTrue(any('coach' in e for e in errs([p])), repr(bad))

    def test_reserved_step_id_all(self):
        p = ok()
        p['steps'][0]['id'] = 'all'
        self.assertTrue(any('reserved' in e for e in errs([p])))

    def test_long_action_is_warning_not_error(self):
        e, w = validate([ok(text='x' * 201)], set())
        self.assertTrue(e == [] and len(w) == 1)

    def test_long_detail_is_fine(self):
        self.assertEqual(validate([ok(detail='x' * 5000)], set()), ([], []))

    def test_does_not_mutate_input(self):
        p = ok()
        before = copy.deepcopy(p)
        validate([p], set())
        self.assertEqual(p, before)

    def test_draft_is_warning_not_error(self):
        p = ok()
        p['draft'] = True
        e, w = validate([p], set())
        self.assertEqual(e, [])
        self.assertEqual(w, ['p1: draft, not source-checked'])

    def test_draft_ids(self):
        d = ok()
        d['draft'] = True
        other = ok()
        other['id'] = 'p2'
        self.assertEqual(draft_ids([d, other, None, 'x']), ['p1'])


class MalformedInputTests(unittest.TestCase):
    def check(self, protocols, needle):
        e, _ = validate(protocols, set())
        self.assertTrue(any(needle in x for x in e), e)

    def test_protocol_is_string(self):
        self.check(['oops'], 'protocol #0')

    def test_protocol_is_none(self):
        self.check([None], 'protocol #0')

    def test_steps_is_dict(self):
        p = ok()
        p['steps'] = {'s1': {}}
        self.check([p], 'steps must be')

    def test_step_is_none(self):
        p = ok()
        p['steps'][1] = None
        self.check([p], 'step #1')

    def test_protocol_id_is_list(self):
        p = ok()
        p['id'] = ['a']
        self.check([p], 'id')

    def test_step_id_is_list(self):
        p = ok()
        p['steps'][0]['id'] = ['a']
        self.check([p], 'step #0')

    def test_unhashable_fields_do_not_raise(self):
        p = ok(fig=['x'], tool={'a': 1}, ask={'q': 'q', 'yes': ['s2'], 'no': {}})
        self.check([p], 'fig')

    def test_protocols_not_a_list(self):
        self.assertEqual(validate({'a': 1}, set())[0], ['protocols must be a list'])


if __name__ == '__main__':
    unittest.main()


class ReportDraftMarkerTests(unittest.TestCase):
    def test_marker_line_is_detected(self):
        from tools.validate import report_wording_is_draft
        self.assertTrue(report_wording_is_draft('a\n  /* REPORT_WORDING_DRAFT */\nb'))
        self.assertTrue(report_wording_is_draft('/* REPORT_WORDING_DRAFT */'))

    def test_marker_only_counts_as_a_whole_line(self):
        from tools.validate import report_wording_is_draft
        self.assertFalse(report_wording_is_draft(''))
        self.assertFalse(report_wording_is_draft('const x = 1;'))
        self.assertFalse(report_wording_is_draft('// mentions REPORT_WORDING_DRAFT in a sentence'))
        self.assertFalse(report_wording_is_draft('x /* REPORT_WORDING_DRAFT */'))

    def test_marker_and_draft_flag_in_reports_js_agree(self):
        import os
        from tools.validate import report_wording_is_draft
        src = open(os.path.join(os.path.dirname(os.path.dirname(__file__)), 'src', 'reports.js'), encoding='utf-8').read()
        self.assertEqual(report_wording_is_draft(src), 'draft: true,' in src)


class ShapeTests(unittest.TestCase):
    """Unknown keys and field shapes (final review, Important 5)."""

    def has(self, p, words):
        es = errs([p])
        self.assertTrue(any(all(w in e for w in words) for e in es), (words, es))

    def test_unknown_protocol_key_is_an_error(self):
        for k in ('dont', 'evacaute', 'warn', 'figSvg'):
            p = ok(); p[k] = ['x']
            self.has(p, ['unknown key', repr(k)])

    def test_unknown_step_key_is_an_error(self):
        for k in ('warning', 'donts', 'timers', 'figSvg'):
            self.has(ok(**{k: 'x'}), ['unknown key', repr(k)])

    def test_every_allowed_key_passes_with_a_good_value(self):
        p = advanced()
        p.update({'keywords': ['k'], 'summary': 'S', 'donts': ['d'], 'evacuate': ['e'], 'notes': ['n'],
                  'draft': False, 'coach': {'compressions': 30, 'breaths': 2}})
        p['steps'][0].update({'detail': 'D', 'warn': 'W', 'log': 'L', 'timer': {'seconds': 60, 'label': 'T'},
                              'tool': 'tq', 'fig': 'f', 'end': False})
        self.assertEqual(validate([p], {'f'})[0], [])

    def test_step_strings(self):
        for k in ('detail', 'warn', 'log'):
            for bad in (5, ['a'], None, {'a': 1}):
                self.has(ok(**{k: bad}), [k, 'must be a string'])

    def test_protocol_summary_and_title_are_strings(self):
        p = ok(); p['summary'] = ['not', 'a string']
        self.has(p, ['summary', 'must be a string'])
        p = ok(); p['title'] = 5
        self.has(p, ['missing title'])

    def test_step_text_must_be_a_string(self):
        self.has(ok(text=['Do it']), ['missing text'])

    def test_timer_shape(self):
        self.assertEqual(errs([ok(timer={'seconds': 1.5, 'label': 'T'})]), [])
        for bad in (60, 'one minute', {'seconds': 0, 'label': 'T'}, {'seconds': -5, 'label': 'T'}, {'seconds': '60', 'label': 'T'},
                    {'seconds': True, 'label': 'T'}, {'seconds': float('nan'), 'label': 'T'}, {'seconds': 60}, {'seconds': 60, 'label': ' '},
                    {'seconds': 60, 'label': 7}):
            self.has(ok(timer=bad), ['timer'])

    def test_lists_of_non_blank_strings(self):
        for k in ('donts', 'evacuate', 'keywords', 'notes', 'indications', 'contraindications', 'equipment', 'complications'):
            for bad in ('a string', [''], ['ok', '  '], [5], ['ok', None], {'a': 'b'}):
                p = advanced() if k in ('indications', 'contraindications', 'equipment', 'complications') else ok()
                p[k] = bad
                self.has(p, [k])

    def test_empty_lists_are_allowed_where_optional(self):
        p = ok(); p.update({'donts': [], 'evacuate': [], 'keywords': []})
        self.assertEqual(errs([p]), [])

    def test_sources_items_need_a_name(self):
        for bad in ([{'year': 2020}], [{'name': ' '}], ['Some Source'], [None], [{'name': 'ok'}, {'url': 'x'}]):
            p = ok(); p['sources'] = bad
            self.has(p, ['source'])

    def test_end_and_draft_are_booleans(self):
        for bad in ('true', 1, None):
            self.has(ok(end=bad), ['end', 'true or false'])
            p = ok(); p['draft'] = bad
            self.has(p, ['draft', 'true or false'])

    def test_tier_only_advanced(self):
        for bad in ('basic', 'Advanced', True, None):
            p = advanced(); p['tier'] = bad
            self.has(p, ['tier'])

    def test_shipped_protocols_pass_unchanged(self):
        import glob, json, os, sys
        root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        sys.path.insert(0, os.path.join(root, 'figs'))
        import figs
        data = [json.load(open(f, encoding='utf-8')) for f in sorted(glob.glob(os.path.join(root, 'src', 'protocols', '*.json')))]
        self.assertGreater(len(data), 40)
        self.assertEqual(validate(data, set(figs.F)), ([], []))


def test_no_figure_id_is_defined_twice():
    import re, os
    src = open(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'figs', 'figs.py'), encoding='utf-8').read()
    ids = re.findall(r"^svg\('([\w-]+)'", src, re.M)
    assert len(ids) > 30 and len(ids) == len(set(ids)), sorted({i for i in ids if ids.count(i) > 1})


def topic(**over):
    t = {
        'id': 'surv-water', 'title': 'Water', 'category': 'water', 'keywords': ['drink'], 'summary': 'Find water.',
        'where': ['town', 'coast'], 'when': ['cold'], 'doFirst': ['Stop.'],
        'sections': [{'h': 'Basics', 'blocks': [
            {'p': 'Text.'}, {'list': ['a', 'b']}, {'steps': ['one', 'two']}, {'warn': 'Careful.'},
            {'table': {'head': ['A', 'B'], 'rows': [['1', '2']]}},
            {'fig': 'f1', 'cap': 'A figure.'}, {'link': 's:surv-other', 'label': 'Other'}]}],
        'sources': [{'name': 'CDC', 'used': 'Boil times'}], 'reviewed': '2026-11-17', 'asOf': '2026-10-01',
    }
    t.update(over)
    return t


def terrs(topics, figs=('f1',), links=('s:surv-other',)):
    return validate_topics(topics, set(figs), set(links))[0]


def checklist(**over):
    c = {'id': 'go-bag', 'title': 'Go bag', 'category': 'basics', 'summary': 'Pack.',
         'items': [{'id': 'i1', 'text': 'Water'}, {'id': 'i2', 'text': 'Radio', 'note': 'Hand crank'}],
         'sources': [{'name': 'Ready.gov', 'used': 'List'}], 'reviewed': '2026-11-17'}
    c.update(over)
    return c


def cerrs(lists):
    return validate_checklists(lists, set())[0]


class TopicValidation(unittest.TestCase):
    def has(self, errors, *parts):
        self.assertTrue(any(all(x in e for x in parts) for e in errors), (parts, errors))

    def test_constants(self):
        self.assertEqual(RESERVED_TOPIC_IDS, {'tool', 'list'})
        self.assertEqual(WHERE, {'town', 'rural', 'woods', 'coast'})
        self.assertEqual(WHEN, {'cold', 'warm'})
        self.assertEqual(TOPIC_CATEGORIES, {'basics', 'water', 'heat', 'radiation', 'food', 'comms', 'staying', 'moving', 'town'})

    def test_valid_topic_has_no_errors(self):
        self.assertEqual(validate_topics([topic()], {'f1'}, {'s:surv-other'}), ([], []))

    def test_minimal_topic_is_valid(self):
        t = topic()
        for k in ('where', 'when', 'doFirst', 'asOf'):
            del t[k]
        self.assertEqual(terrs([t]), [])

    def test_bad_ids(self):
        for bad in ('water', 'surv-', 'surv-Water', 'surv-' + 'a' * 56, 'surv-a b'):
            self.has(terrs([topic(id=bad)]), repr(bad), 'surv-')
        self.has(terrs([topic(), topic()]), "'surv-water'", 'duplicate')

    def test_reserved_ids_are_listed(self):
        # 'tool' and 'list' can never match surv-*, so the pattern error carries the point; the set stays for the router.
        self.assertTrue(terrs([topic(id='tool')]))

    def test_reserved_id_check_runs_on_its_own(self):
        import tools.validate as v
        old = v.RESERVED_TOPIC_IDS
        v.RESERVED_TOPIC_IDS = old | {'surv-x'}
        try:
            self.has(terrs([topic(id='surv-x')]), "'surv-x'", 'reserved')
        finally:
            v.RESERVED_TOPIC_IDS = old

    def test_unknown_keys(self):
        self.has(terrs([topic(extra=1)]), "'surv-water'", "unknown key 'extra'")
        t = topic(); t['sections'][0]['blocks'][0]['zz'] = 1
        self.has(terrs([t]), "'surv-water'", "unknown key 'zz'")
        t = topic(); t['sections'][0]['bad'] = 1
        self.has(terrs([t]), "unknown key 'bad'")

    def test_build_added_fig_keys_are_unknown_in_source(self):
        t = topic(); t['sections'][0]['blocks'][5]['figSvg'] = '<svg/>'
        self.has(terrs([t]), "unknown key 'figSvg'")
        t = topic(); t['sections'][0]['blocks'][5]['figLabel'] = 'x'
        self.has(terrs([t]), "unknown key 'figLabel'")

    def test_block_with_two_shapes(self):
        t = topic(); t['sections'][0]['blocks'] = [{'p': 'a', 'warn': 'b'}]
        self.has(terrs([t]), "'surv-water'", 'exactly one')
        t['sections'][0]['blocks'] = [{}]
        self.has(terrs([t]), 'exactly one')
        t['sections'][0]['blocks'] = ['text']
        self.has(terrs([t]), 'must be an object')

    def test_sections(self):
        self.has(terrs([topic(sections=[])]), "'surv-water'", 'sections')
        self.has(terrs([topic(sections=None)]), 'sections')
        t = topic(); del t['sections'][0]['h']
        self.has(terrs([t]), 'missing h')
        t = topic(); t['sections'][0]['blocks'] = []
        self.has(terrs([t]), 'blocks')
        self.has(terrs([topic(sections=['x'])]), 'must be an object')

    def test_category_where_when(self):
        self.has(terrs([topic(category='nope')]), "'surv-water'", "unknown category 'nope'")
        self.has(terrs([topic(category=None)]), 'missing category')
        self.has(terrs([topic(where=['moon'])]), "'surv-water'", "where", "'moon'")
        self.has(terrs([topic(when=['spring'])]), "when", "'spring'")
        self.has(terrs([topic(where='town')]), 'where must be a list')

    def test_fig_and_link_references(self):
        self.has(terrs([topic()], figs=()), "'surv-water'", "unknown figure 'f1'")
        t = topic(); del t['sections'][0]['blocks'][5]['cap']
        self.has(terrs([t]), 'fig', 'cap')
        self.has(terrs([topic()], links=()), "'surv-water'", "unknown link 's:surv-other'")
        t = topic(); del t['sections'][0]['blocks'][6]['label']
        self.has(terrs([t]), 'link', 'label')

    def test_block_value_types(self):
        for blk in ({'p': ''}, {'warn': ' '}, {'list': []}, {'list': ['']}, {'steps': 'x'}, {'steps': [1]},
                    {'table': 'x'}, {'table': {'head': [], 'rows': [['a']]}}, {'table': {'head': ['A'], 'rows': []}}):
            t = topic(); t['sections'][0]['blocks'] = [blk]
            self.assertTrue(terrs([t]), blk)

    def test_table_row_length(self):
        t = topic(); t['sections'][0]['blocks'] = [{'table': {'head': ['A', 'B'], 'rows': [['1', '2'], ['3']]}}]
        self.has(terrs([t]), "'surv-water'", 'row 2', 'head')
        t['sections'][0]['blocks'] = [{'table': {'head': ['A'], 'rows': [['1']], 'x': 1}}]
        self.has(terrs([t]), "unknown key 'x'")

    def test_sources(self):
        for bad in (None, [], 'x'):
            t = topic(sources=bad)
            self.has(terrs([t]), "'surv-water'", 'sources')
        t = topic(); del t['sources']
        self.has(terrs([t]), 'sources')
        self.has(terrs([topic(sources=[{'used': 'x'}])]), 'name')
        self.has(terrs([topic(sources=[{'name': 'x'}])]), 'used')
        self.has(terrs([topic(sources=['x'])]), 'name')

    def test_dates(self):
        t = topic(); del t['reviewed']
        self.has(terrs([t]), "'surv-water'", 'missing reviewed')
        self.has(terrs([topic(reviewed='17/11/2026')]), 'reviewed', 'YYYY-MM-DD')
        self.has(terrs([topic(asOf='2026-13-01')]), 'asOf', 'YYYY-MM-DD')
        self.has(terrs([topic(asOf='Oct 2026')]), 'asOf', 'YYYY-MM-DD')
        self.has(terrs([topic(asOf=None)]), 'asOf', 'YYYY-MM-DD')

    def test_other_field_types(self):
        self.has(terrs([topic(title='')]), 'missing title')
        self.has(terrs([topic(keywords='x')]), 'keywords')
        self.has(terrs([topic(doFirst=[''])]), 'doFirst')
        self.has(terrs([topic(summary=3)]), 'summary')
        self.has(terrs([topic(draft='yes')]), 'draft')

    def test_draft_is_warning_not_error(self):
        errors, warnings = validate_topics([topic(draft=True)], {'f1'}, {'s:surv-other'})
        self.assertEqual(errors, [])
        self.assertEqual(len(warnings), 1)
        self.assertIn('surv-water', warnings[0])
        self.assertEqual(topic_draft_ids([topic(draft=True), topic(id='surv-b'), 'x', {'draft': True}]), ['surv-water'])

    def test_non_dict_inputs_do_not_raise(self):
        for bad in ('x', None, 5, ['x'], [None], {'a': 1}):
            r = validate_topics(bad, set(), set())
            self.assertTrue(r[0], bad)
        self.assertTrue(validate_topics([topic(sections=[None])], set(), set())[0])

    def test_input_not_mutated(self):
        t = topic(draft=True); before = copy.deepcopy(t)
        validate_topics([t], {'f1'}, {'s:surv-other'}); validate_topics([t], set(), set())
        self.assertEqual(t, before)
        fig, links = {'f1'}, {'s:surv-other'}
        validate_topics([t], fig, links)
        self.assertEqual((fig, links), ({'f1'}, {'s:surv-other'}))


class ChecklistValidation(unittest.TestCase):
    def has(self, errors, *parts):
        self.assertTrue(any(all(x in e for x in parts) for e in errors), (parts, errors))

    def test_valid_checklist(self):
        self.assertEqual(validate_checklists([checklist()], set()), ([], []))

    def test_minimal_checklist_is_valid(self):
        c = checklist(); del c['summary']
        self.assertEqual(cerrs([c]), [])

    def test_id_rules(self):
        self.has(cerrs([checklist(id='Bad Id')]), "'Bad Id'", 'id')
        self.has(cerrs([checklist(), checklist()]), "'go-bag'", 'duplicate')

    def test_unknown_keys(self):
        self.has(cerrs([checklist(extra=1)]), "'go-bag'", "unknown key 'extra'")
        c = checklist(); c['items'][0]['zz'] = 1
        self.has(cerrs([c]), "unknown key 'zz'")

    def test_category(self):
        self.has(cerrs([checklist(category='nope')]), "'go-bag'", "unknown category 'nope'")

    def test_items(self):
        self.has(cerrs([checklist(items=[])]), "'go-bag'", 'items')
        self.has(cerrs([checklist(items=None)]), 'items')
        c = checklist(); c['items'][1]['id'] = 'i1'
        self.has(cerrs([c]), "'go-bag'", 'duplicate item id', "'i1'")
        c = checklist(); c['items'][0]['text'] = '  '
        self.has(cerrs([c]), "'go-bag'", 'text')
        c = checklist(); c['items'][0]['id'] = 'Bad'
        self.has(cerrs([c]), 'item id')
        c = checklist(); c['items'][1]['note'] = ''
        self.has(cerrs([c]), 'note')
        self.has(cerrs([checklist(items=['x'])]), 'must be an object')

    def test_sources_and_reviewed(self):
        self.has(cerrs([checklist(sources=[])]), "'go-bag'", 'sources')
        self.has(cerrs([checklist(sources=[{'name': 'x'}])]), 'used')
        c = checklist(); del c['reviewed']
        self.has(cerrs([c]), 'missing reviewed')
        self.has(cerrs([checklist(reviewed='yesterday')]), 'YYYY-MM-DD')
        self.has(cerrs([checklist(title='')]), 'missing title')
        self.has(cerrs([checklist(summary=4)]), 'summary')

    def test_draft(self):
        errors, warnings = validate_checklists([checklist(draft=True)], set())
        self.assertEqual(errors, [])
        self.assertIn('go-bag', warnings[0])
        self.assertEqual(topic_draft_ids([checklist(draft=True), checklist(id='b')]), ['go-bag'])
        self.has(cerrs([checklist(draft=1)]), 'draft')

    def test_non_dict_inputs_do_not_raise(self):
        for bad in ('x', None, ['x'], [None], [5]):
            self.assertTrue(validate_checklists(bad, set())[0], bad)

    def test_input_not_mutated(self):
        c = checklist(draft=True); before = copy.deepcopy(c)
        validate_checklists([c], set())
        self.assertEqual(c, before)


def qty_item(**over):
    q = {'amount': 1, 'unit': 'gallon', 'per': 'personDay'}
    q.update(over)
    return q


class ChecklistQuantity(unittest.TestCase):
    def has(self, errors, *parts):
        self.assertTrue(any(all(x in e for x in parts) for e in errors), (parts, errors))

    def with_qty(self, qty):
        c = checklist(); c['items'][0]['qty'] = qty
        return cerrs([c])

    def test_valid_quantities(self):
        for q in (qty_item(), qty_item(amount=0.5, unit='litre', per='person'), qty_item(amount=2.5)):
            self.assertEqual(self.with_qty(q), [], q)

    def test_amount_must_be_a_positive_number(self):
        for bad in (0, -1, '2', None, True, float('nan'), float('inf')):
            self.has(self.with_qty(qty_item(amount=bad)), "'go-bag'", 'qty', 'amount')
        c = checklist(); c['items'][0]['qty'] = {'unit': 'gallon', 'per': 'person'}
        self.has(cerrs([c]), 'qty', 'amount')

    def test_unit_must_not_be_blank(self):
        for bad in ('', '  ', None, 3):
            self.has(self.with_qty(qty_item(unit=bad)), 'qty', 'unit')

    def test_per_must_be_one_of_two_values(self):
        for bad in ('day', 'Person', '', None, 1):
            self.has(self.with_qty(qty_item(per=bad)), 'qty', 'per')
        self.has(self.with_qty(qty_item(per='group')), "'group'")

    def test_unknown_key_and_non_object(self):
        self.has(self.with_qty(qty_item(extra=1)), 'qty', "unknown key 'extra'")
        for bad in ('1 gallon', 4, None, ['x']):
            self.has(self.with_qty(bad), 'qty', 'object')


def tooldata(**over):
    t = {'id': 'water', 'title': 'Water', 'values': {
            'perPersonDay': {'value': 1, 'unit': 'gallon'},
            'boilMinutes': {'value': 1, 'unit': 'minute', 'note': '3 above 5,000 ft'}},
         'sources': [{'name': 'CDC', 'used': 'Daily water'}], 'reviewed': '2026-11-18'}
    t.update(over)
    return t


def derrs(items):
    return validate_tooldata(items)[0]


def gridded(**over):
    """A small wind chill style tool with a valid chart grid; keyword args replace grid keys."""
    g = {'temps': [10, 5, 0], 'winds': [5, 10, 15],
         'chill': [[6, 0, -5], [3, -4, -10], [0, -7, -13]],
         'bands': [[0, 0, 30], [0, 30, 30], [30, 30, 10]],
         'bandMinutes': [10, 30]}
    g.update(over)
    return tooldata(id='windchill', title='Wind chill', grid=g)


def gerrs(**over):
    return derrs([gridded(**over)])


class ToolDataValidation(unittest.TestCase):
    def has(self, errors, *parts):
        self.assertTrue(any(all(x in e for x in parts) for e in errors), (parts, errors))

    def test_tool_names(self):
        self.assertEqual(TOOL_NAMES, ('daylight', 'sos', 'water', 'windchill'))

    def test_valid_and_empty(self):
        self.assertEqual(validate_tooldata([tooldata()]), ([], []))
        self.assertEqual(validate_tooldata([]), ([], []))

    def test_id_rules(self):
        for bad in ('Bad', '1water', 'a_b', 'w' * 41, '', None, 5):
            self.assertTrue(derrs([tooldata(id=bad)]), bad)
        self.has(derrs([tooldata(id='Bad')]), "'Bad'", 'id')
        self.assertEqual(derrs([tooldata(id='w' * 40)]), [])
        self.has(derrs([tooldata(), tooldata()]), "'water'", 'duplicate')

    def test_unknown_keys(self):
        self.has(derrs([tooldata(extra=1)]), "'water'", "unknown key 'extra'")
        t = tooldata(); t['values']['boilMinutes']['zz'] = 1
        self.has(derrs([t]), "'water'", 'boilMinutes', "unknown key 'zz'")

    def test_values_must_not_be_empty(self):
        self.has(derrs([tooldata(values={})]), "'water'", 'values')
        self.has(derrs([tooldata(values=None)]), 'values')
        self.has(derrs([tooldata(values=[1])]), 'values')
        t = tooldata(); del t['values']
        self.has(derrs([t]), 'values')

    def test_value_must_be_a_finite_number(self):
        for bad in ('1', None, True, float('nan'), float('inf'), float('-inf'), [1]):
            t = tooldata(); t['values']['boilMinutes']['value'] = bad
            self.has(derrs([t]), "'water'", 'boilMinutes', 'value')
        t = tooldata(); del t['values']['boilMinutes']['value']
        self.has(derrs([t]), 'boilMinutes', 'value')

    def test_value_must_be_greater_than_zero(self):
        for bad in (0, -1, -0.5, 0.0):
            t = tooldata(); t['values']['boilMinutes']['value'] = bad
            self.has(derrs([t]), "'water'", 'boilMinutes', 'greater than 0')
        t = tooldata(); t['values']['boilMinutes']['value'] = 0.001
        self.assertEqual(derrs([t]), [])

    def test_extra_values_need_a_note(self):
        t = tooldata(); t['values']['extraHotPerPersonDay'] = {'value': 1, 'unit': 'gal'}
        self.has(derrs([t]), "'water'", 'extraHotPerPersonDay', 'note')
        t['values']['extraHotPerPersonDay']['note'] = '  '
        self.has(derrs([t]), 'extraHotPerPersonDay', 'note')
        t['values']['extraHotPerPersonDay']['note'] = 'Hot weather'
        self.assertEqual(derrs([t]), [])

    def test_unit_is_required(self):
        for bad in ('', '  ', None, 2):
            t = tooldata(); t['values']['boilMinutes']['unit'] = bad
            self.has(derrs([t]), "'water'", 'boilMinutes', 'unit')
        t = tooldata(); del t['values']['boilMinutes']['unit']
        self.has(derrs([t]), 'boilMinutes', 'unit')

    def test_note_and_value_entry_shape(self):
        t = tooldata(); t['values']['boilMinutes']['note'] = ''
        self.has(derrs([t]), 'boilMinutes', 'note')
        self.has(derrs([tooldata(values={'x': 5})]), "'x'", 'object')
        self.has(derrs([tooldata(values={'': {'value': 1, 'unit': 'u'}})]), 'name')

    def test_title_sources_reviewed(self):
        self.has(derrs([tooldata(title='')]), "'water'", 'title')
        self.has(derrs([tooldata(sources=[])]), "'water'", 'sources')
        self.has(derrs([tooldata(sources=[{'name': 'x'}])]), 'used')
        t = tooldata(); del t['sources']
        self.has(derrs([t]), 'sources')
        t = tooldata(); del t['reviewed']
        self.has(derrs([t]), 'missing reviewed')
        self.has(derrs([tooldata(reviewed='soon')]), 'YYYY-MM-DD')

    def test_draft_is_a_warning(self):
        errors, warnings = validate_tooldata([tooldata(draft=True)])
        self.assertEqual(errors, [])
        self.assertIn('water', warnings[0])
        self.assertEqual(topic_draft_ids([tooldata(draft=True), tooldata(id='b')]), ['water'])
        self.has(derrs([tooldata(draft=1)]), 'draft')

    def test_grid_valid_and_absent(self):
        self.assertEqual(validate_tooldata([gridded()]), ([], []))
        self.assertEqual(validate_tooldata([tooldata()]), ([], []))

    def test_grid_must_be_an_object(self):
        for bad in (None, [], 'x', 5):
            self.has(derrs([tooldata(id='windchill', grid=bad)]), "'windchill'", 'grid', 'object')

    def test_grid_keys_are_exact(self):
        self.has(gerrs(extra=1), "'windchill'", 'grid', "unknown key 'extra'")
        for k in ('temps', 'winds', 'chill', 'bands', 'bandMinutes'):
            g = gridded()['grid']; del g[k]
            self.has(derrs([tooldata(id='windchill', grid=g)]), "'windchill'", 'grid', k)

    def test_grid_temps(self):
        for bad in ([], 'x', None, [10, 'a', 0], [10, True, 0], [10, 10, 0], [0, 5, 10], [10, float('nan'), 0]):
            self.has(gerrs(temps=bad), "'windchill'", 'temps')

    def test_grid_winds(self):
        for bad in ([], 'x', None, [0, 10, 15], [-5, 10, 15], [5, 5, 15], [15, 10, 5], [5, 'a', 15]):
            self.has(gerrs(winds=bad), "'windchill'", 'winds')

    def test_grid_band_minutes(self):
        for bad in ([], 'x', None, [0, 30], [-10, 30], [30, 10], [10, 10], [10, 'a']):
            self.has(gerrs(bandMinutes=bad), "'windchill'", 'bandMinutes')

    def test_grid_row_counts_and_ragged_rows(self):
        for k in ('chill', 'bands'):
            g = gridded()['grid'][k]
            self.has(gerrs(**{k: g[:2]}), "'windchill'", k, 'rows')
            self.has(gerrs(**{k: g + [g[0]]}), "'windchill'", k, 'rows')
            self.has(gerrs(**{k: 'x'}), "'windchill'", k)
            self.has(gerrs(**{k: [g[0], g[1][:2], g[2]]}), "'windchill'", k, 'row', 'columns')
            self.has(gerrs(**{k: [g[0], 'x', g[2]]}), "'windchill'", k, 'row')

    def test_grid_chill_cells_are_finite_numbers(self):
        for bad in (float('nan'), float('inf'), float('-inf'), 'x', None, True):
            c = [list(r) for r in gridded()['grid']['chill']]; c[1][1] = bad
            self.has(gerrs(chill=c), "'windchill'", 'chill')

    def test_grid_band_cells_are_zero_or_a_legend_value(self):
        for bad in (5, 20, -1, '30', None, 30.5):
            b = [list(r) for r in gridded()['grid']['bands']]; b[0][0] = bad
            self.has(gerrs(bands=b), "'windchill'", 'bands')

    def test_grid_band_never_gets_less_severe(self):
        # wind rises down a column: 30 then 0 is a slip
        b = [[0, 0, 30], [0, 30, 30], [30, 30, 10]]
        b[2][2] = 0
        self.has(gerrs(bands=b), "'windchill'", 'bands', 'less severe')
        # temperature falls along a row: 10 then 30 is a slip
        b = [[0, 0, 30], [0, 30, 30], [30, 30, 10]]
        b[2][0] = 10
        self.has(gerrs(bands=b), "'windchill'", 'bands', 'less severe')
        b = [[0, 0, 30], [0, 30, 30], [30, 30, 10]]
        b[1][2] = 0
        self.has(gerrs(bands=b), "'windchill'", 'bands', 'less severe')
        # equal bands and 0 to a number are fine; a shorter time is more severe
        ok = [[0, 0, 0], [0, 0, 30], [0, 30, 10]]
        self.assertEqual(gerrs(bands=ok), [])

    def test_non_dict_inputs_do_not_raise(self):
        for bad in ('x', None, 5, {}, ['x'], [None], [5], [[]]):
            self.assertTrue(derrs(bad), bad)

    def test_input_not_mutated(self):
        t = tooldata(draft=True); before = copy.deepcopy(t)
        validate_tooldata([t])
        self.assertEqual(t, before)
