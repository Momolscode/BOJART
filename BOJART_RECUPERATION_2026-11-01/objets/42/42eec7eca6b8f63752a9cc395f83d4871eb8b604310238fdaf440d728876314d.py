import concurrent.futures
import tempfile
from pathlib import Path
import unittest
from commandes import Commandes, Conflict, Denied


class OrchestrationTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.path = Path(self.tmp.name) / 'test.sqlite'
        self.c = Commandes(self.path)
        self.configure('studio')

    def tearDown(self):
        self.c.close()
        self.tmp.cleanup()

    def configure(self, project):
        self.c.configure(project, 'plan-test', cap_units=100, unit='test-unit',
                         actions=['read.status', 'fake.render'], authority_ref='fixture:test-only', max_inflight=3)

    def enqueue(self, key='one', cost=10):
        return self.c.enqueue('studio', 'plan-test', key, 'fake.render', {'scene':'fictive'}, quote_units=cost)

    def test_duplicate_uses_same_command_and_one_reservation(self):
        a = self.enqueue()
        self.assertEqual(a, self.enqueue())
        self.assertEqual(len(self.c.events('studio')), 1)

    def test_reused_key_changed_payload_rejected(self):
        self.enqueue()
        with self.assertRaises(Conflict):
            self.c.enqueue('studio', 'plan-test', 'one', 'fake.render', {'other':True}, quote_units=10)

    def test_project_scope_and_plan_separated(self):
        a = self.enqueue()
        with self.assertRaises(KeyError): self.c.get('atelier', a['command_id'])
        with self.assertRaises(Denied):
            self.c.enqueue('atelier', 'plan-test', 'one', 'fake.render', {})
        self.configure('atelier')
        b = self.c.enqueue('atelier', 'plan-test', 'one', 'fake.render', {})
        self.assertNotEqual(a['command_id'], b['command_id'])

    def test_unauthorized_action_refused(self):
        with self.assertRaises(Denied):
            self.c.enqueue('studio', 'plan-test', 'one', 'social.publish', {})

    def test_cap_includes_other_reserved_commands(self):
        self.enqueue(cost=80)
        with self.assertRaises(Denied): self.enqueue('two', 21)
        self.assertEqual(len(self.c.list('studio')), 1)

    def test_policy_cannot_silently_raise_cap(self):
        with self.assertRaises(Conflict):
            self.c.configure('studio','plan-test',cap_units=101,unit='test-unit',
                             actions=['read.status','fake.render'],authority_ref='fixture:test-only',max_inflight=3)

    def test_unknown_after_dispatch_cannot_be_resubmitted(self):
        a = self.enqueue(); b = self.c.dispatch('studio',a['command_id'],1)
        self.c.unknown('studio',a['command_id'],b['revision'])
        with self.assertRaises(Denied): self.c.dispatch('studio',a['command_id'],3)
        self.assertEqual(self.enqueue()['state'],'unknown')

    def test_reopen_after_crash_keeps_submitting_and_blocks_retry(self):
        a = self.enqueue(); self.c.dispatch('studio',a['command_id'],1)
        self.c.close(); self.c=Commandes(self.path)
        self.assertEqual(self.c.get('studio',a['command_id'])['state'],'submitting')
        with self.assertRaises(Denied): self.c.dispatch('studio',a['command_id'],2)

    def test_unknown_can_be_reconciled_with_existing_job(self):
        a=self.enqueue(); cid=a['command_id']; self.c.dispatch('studio',cid,1)
        self.c.unknown('studio',cid,2)
        self.c.receipt('studio',cid,3,'fake-job-1')
        r=self.c.receipt('studio',cid,4,'fake-job-1',state='verified',proof_refs=['fixture:verified'],actual_units=10)
        self.assertEqual(r['state'],'verified')
        with self.assertRaises(Denied): self.c.dispatch('studio',cid,5)

    def test_job_identity_and_revision_checked(self):
        a=self.enqueue(); cid=a['command_id']; self.c.dispatch('studio',cid,1)
        self.c.receipt('studio',cid,2,'job-a')
        with self.assertRaises(Conflict): self.c.receipt('studio',cid,2,'job-a')
        with self.assertRaises(Conflict): self.c.receipt('studio',cid,3,'job-b')

    def test_completion_requires_proof(self):
        a=self.enqueue();cid=a['command_id'];self.c.dispatch('studio',cid,1)
        with self.assertRaises(ValueError): self.c.receipt('studio',cid,2,'job-a',state='verified')
        self.assertEqual(self.c.get('studio',cid)['revision'],2)

    def test_cancel_only_before_dispatch(self):
        a=self.enqueue(cost=100);self.c.cancel_prepared('studio',a['command_id'],1)
        b=self.enqueue('two',100);self.c.dispatch('studio',b['command_id'],1)
        with self.assertRaises(Denied): self.c.cancel_prepared('studio',b['command_id'],2)

    def test_terminal_unknown_cost_keeps_reservation(self):
        a=self.enqueue(cost=90);cid=a['command_id'];self.c.dispatch('studio',cid,1)
        self.c.receipt('studio',cid,2,'job-a',state='verified',proof_refs=['fixture:result'])
        with self.assertRaises(Denied): self.enqueue('two',11)

    def test_real_overrun_recorded_and_blocks_future_spend(self):
        a=self.enqueue(cost=90);cid=a['command_id'];self.c.dispatch('studio',cid,1)
        r=self.c.receipt('studio',cid,2,'job-a',state='verified',proof_refs=['fixture:result'],actual_units=105)
        self.assertTrue(r['overrun'])
        with self.assertRaises(Denied): self.enqueue('two',1)

    def test_inflight_is_project_wide_across_plans(self):
        self.enqueue('one');self.enqueue('two');self.enqueue('three')
        self.c.configure('studio','new-plan',cap_units=0,unit='test-unit',actions=['read.status'],
                         authority_ref='fixture:other-plan',max_inflight=3)
        with self.assertRaises(Denied): self.c.enqueue('studio','new-plan','four','read.status',{})

    def test_two_workers_one_dispatch_wins(self):
        a=self.enqueue();cid=a['command_id']
        def dispatch():
            c=Commandes(self.path)
            try:
                c.dispatch('studio',cid,1)
                return 'winner'
            except (Conflict,Denied): return 'refused'
            finally: c.close()
        with concurrent.futures.ThreadPoolExecutor(2) as ex:
            self.assertCountEqual(list(ex.map(lambda _:dispatch(),range(2))),['winner','refused'])

    def test_unum_projection_exact_shape_and_unknown_preserved(self):
        a=self.enqueue();cid=a['command_id'];self.c.dispatch('studio',cid,1);self.c.unknown('studio',cid,2)
        p=self.c.unum_projection('studio',cid)
        self.assertEqual(set(p),{'id','state','sourceDate','evidence'})
        self.assertEqual(p['state'],'unknown')
        self.assertLessEqual(len(p['id']),80)

    def test_invalid_money_never_enters_journal(self):
        for cost in [-1,True,1.1,float('nan')]:
            with self.assertRaises(ValueError): self.enqueue(cost=cost)
        self.assertEqual(self.c.events('studio'),[])


if __name__=='__main__': unittest.main()
