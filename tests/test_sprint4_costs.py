from app.observability.costs import estimate_cost, alerts

def test_estimated_cost():
    assert estimate_cost(1_000_000, 500_000, 1, 2)==2.0

def test_alerts():
    rows=[{"provider":"ollama","requests":10,"successful":5,"avg_latency_ms":15000}]
    result=alerts(rows)
    assert len(result)==2
