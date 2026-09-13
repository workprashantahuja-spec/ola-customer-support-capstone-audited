"""Read-only product probes; write a separate audit, never overwrite old evidence."""
import copy
import json
import tempfile
from pathlib import Path
from unittest.mock import patch

from fastapi.testclient import TestClient
from api_app import create_app
from crew_workflow import SupportCrewWorkflow
from evaluation import DeterministicMockJudge, EVALUATION_CASES
from governance import RuntimeBudget
from grounded_answers import GroundedAnswerEngine
from guardrails import validate_grounded_output
from ticket_lookup import check_support_ticket_status


def run():
    findings = {}
    evidence = check_support_ticket_status('SUP-0014')
    draft = SupportCrewWorkflow().run_ticket('SUP-0014')
    altered = draft.model_copy(update={'answer': 'Your refund is approved for INR 50000.'})
    try:
        validate_grounded_output(altered, evidence)
        findings['ticket_guard_accepts_invented_answer'] = True
    except ValueError:
        findings['ticket_guard_accepts_invented_answer'] = False

    saved = json.loads((Path(__file__).parent / 'transcripts/portion9_evaluation.json').read_text())
    observed = copy.deepcopy(saved['results'][0]['observed'])
    invented = ' All riders are entitled to INR 50000 compensation automatically.'
    observed['reply']['message'] += invented
    observed['reply']['response']['answer'] += invented
    observed['final_answer'] += invented
    scores, _ = DeterministicMockJudge().judge(EVALUATION_CASES[0], observed)
    findings['judge_scores_with_invented_claim'] = scores.model_dump()
    findings['long_unbroken_input_budget'] = RuntimeBudget().inspect('word' * 900).to_dict()

    class ChangingIndex:
        def __init__(self):
            self.calls = 0
            self.text = 'Policy\nOld policy.'
        def query(self, *args):
            self.calls += 1
            return {'hits': [{'cosine_similarity': 0.9,
                'source': 'knowledge_base/example.md', 'text': self.text}]}

    index = ChangingIndex()
    with patch.object(GroundedAnswerEngine, '_cache_namespace', return_value='version-one') as fingerprint:
        engine = GroundedAnswerEngine(index=index)
        engine.answer('policy question')
        index.text = 'Policy\nNew policy.'
        fingerprint.return_value = 'version-two'
        result = engine.answer('policy question')
        findings['cache_after_source_version_change'] = {
            'answer': result['answer'], 'cache_hit': result['cache_hit'],
            'retrieval_calls': index.calls, 'fingerprint_calls': fingerprint.call_count,
            'scope': 'Injected source-version change; real handbook files untouched',
        }

    with tempfile.TemporaryDirectory() as temp:
        path = Path(temp) / 'requests.jsonl'
        client = TestClient(create_app(log_path=path), raise_server_exceptions=False)
        rows = []
        for label, payload in [
            ('missing_message', {'session_id': 'audit'}),
            ('whitespace_message', {'session_id': 'audit', 'message': '   '}),
            ('unknown_ticket', {'session_id': 'audit', 'message': 'Check SUP-9999.'}),
        ]:
            before = len(path.read_text().splitlines()) if path.exists() else 0
            response = client.post('/ask', json=payload)
            after = len(path.read_text().splitlines()) if path.exists() else 0
            rows.append({'case': label, 'http_status': response.status_code,
                         'new_log_entries': after - before})
        findings['api_failure_paths'] = rows
        fabricated_phone = '9876543210'
        client.post('/sessions/' + fabricated_phone + '/reset')
        records = [json.loads(line) for line in path.read_text().splitlines()]
        findings['fabricated_phone_survives_in_log_session_id'] = any(
            record.get('session_id') == fabricated_phone for record in records)

    engine = GroundedAnswerEngine()
    paraphrase = engine.answer('Who handles a suspected account takeover?')
    findings['unselected_natural_paraphrase'] = {
        'query': paraphrase['question'], 'fallback': paraphrase['fallback'],
        'top_similarity': paraphrase['top_similarity'],
        'note': 'This earlier trial failed before the evaluated wording was selected; not held-out evaluation.',
    }
    assert not findings['ticket_guard_accepts_invented_answer']
    assert findings['judge_scores_with_invented_claim']['grounding'] == 1
    assert not findings['long_unbroken_input_budget']['accepted']
    assert findings['cache_after_source_version_change']['answer'] == 'New policy.'
    assert all(row['new_log_entries'] == 1 and row['http_status'] < 500
               for row in findings['api_failure_paths'])
    assert not findings['fabricated_phone_survives_in_log_session_id']
    return {'audit_status': 'TARGETED_REPAIRS_PASS_WITH_DOCUMENTED_LIMITS', 'findings': findings}


if __name__ == '__main__':
    report = run()
    destination = Path(__file__).parent / 'transcripts/audit10a_evidence.json'
    destination.write_text(json.dumps(report, indent=2) + '\n')
    print(json.dumps(report, indent=2))
