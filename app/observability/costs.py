"""Sprint 4 prototype estimates; not a billing system."""
def estimate_cost(estimated_input_tokens, estimated_output_tokens,
                  input_usd_per_million=0.0, output_usd_per_million=0.0):
    if min(estimated_input_tokens, estimated_output_tokens,
           input_usd_per_million, output_usd_per_million) < 0:
        raise ValueError("Negative token count or rate")
    return round((estimated_input_tokens * input_usd_per_million +
                  estimated_output_tokens * output_usd_per_million) / 1_000_000, 6)

def alerts(rows, *, failure_rate_threshold=0.2, latency_threshold_ms=10000):
    warnings = []
    for row in rows:
        total = row["requests"]
        if total and (total - row["successful"]) / total >= failure_rate_threshold:
            warnings.append({"provider":row["provider"],"alert":"high_failure_rate"})
        if row["avg_latency_ms"] >= latency_threshold_ms:
            warnings.append({"provider":row["provider"],"alert":"high_latency"})
    return warnings
