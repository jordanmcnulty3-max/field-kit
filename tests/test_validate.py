import copy
import unittest

from tools.validate import draft_ids, validate


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
