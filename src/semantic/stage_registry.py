STAGES = ["step1_signals", "step2_candidates", "step3_recommend", "step4_review", "step5_finalize"]

def next_stage(completed):
    for s in STAGES:
        if s not in completed:
            return s
    return None
