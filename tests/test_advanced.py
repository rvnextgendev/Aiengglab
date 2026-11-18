import pytest
from app.advanced import price_tool, route, ask_advanced, add_text_document
from app.evaluation import evaluate

def test_price():
    assert price_tool('premium', 2, 10)['total_inr'] == 8100

def test_price_validation():
    with pytest.raises(ValueError):
        price_tool('starter', 1, 99)

def test_route():
    assert route('Calculate premium price') == 'price_tool'

def test_session():
    first = ask_advanced('How many paid leave days?')
    second = ask_advanced('What are working hours?', session_id=first['session_id'])
    assert second['history_length'] == 2

def test_eval():
    assert evaluate()['cases'] == 5

def test_upload_filename():
    with pytest.raises(ValueError):
        add_text_document('../evil.py', 'bad')
