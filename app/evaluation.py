"""Tiny reproducible evaluation set; heuristic checks, not a full LLM judge."""
import json
from pathlib import Path
from app.advanced import ask_advanced
ROOT = Path(__file__).resolve().parents[1]

def evaluate() -> dict:
    cases = json.loads((ROOT / 'data' / 'eval_cases.json').read_text(encoding='utf-8'))
    details = []
    for case in cases:
        result = ask_advanced(case['question'], use_llm=False)
        passed = case['expected_substring'].lower() in result['answer'].lower()
        details.append({'question': case['question'], 'passed': passed, 'tool': result['tool'],
                        'latency_ms': result['latency_ms']})
    return {'accuracy': round(sum(d['passed'] for d in details) / len(details), 3),
            'cases': len(details), 'details': details}

if __name__ == '__main__':
    print(json.dumps(evaluate(), indent=2))
