"""
Runtime monitoring using a learned DTMC and PRISM model checker.
Given a trace and a DTMC, computes the probability of reaching unsafe states
at each step and alerts when the probability exceeds a threshold.

Usage:
    cd src/
    python3 monitor_dtmc.py sample_traces/trace_00.json \
        --dtmc dtmc_out/dtmc.prism \
        --model dtmc_out/model.json \
        --predicates pedestrian_npc \
        --threshold 0.9 \
        --bound 5
"""

import os
import json
import re
import subprocess
import argparse
import shutil
from learn_dtmc import encode, PREDICATE_SETS, Predicate

PRISM_BIN = os.path.join(os.path.dirname(__file__), "..", "prism", "bin", "prism")


def find_unsafe_states(states, state_idx):
    """Return state indices where collision bit is set (bit 0 = '1')."""
    return [int(state_idx[s]) for s in states if s.startswith("1")]


def build_pctl(unsafe_indices, bound=-1):
    if len(unsafe_indices) == 1:
        state_expr = f"s={unsafe_indices[0]}"
    else:
        state_expr = "(" + "|".join(f"s={u}" for u in unsafe_indices) + ")"
    if bound > 0:
        return f'P=? [ F<={bound} ({state_expr}) ]'
    return f'P=? [ F ({state_expr}) ]'


def check_reachability(dtmc_path, current_state_idx, pctl_formula, cache=None):
    if cache is not None and current_state_idx in cache:
        return cache[current_state_idx]

    with open(dtmc_path, "r") as f:
        model_txt = f.read()

    updated = re.sub(r"init\s+\d+", f"init {current_state_idx}", model_txt)

    tmp_path = dtmc_path + ".tmp"
    with open(tmp_path, "w") as f:
        f.write(updated)

    cmd = f'{PRISM_BIN} {tmp_path} -pf "{pctl_formula}"'
    result = subprocess.run(cmd, shell=True, capture_output=True, text=True)

    match = re.search(r"Result:\s*([0-9.eE+-]+)", result.stdout)
    if match:
        prob = float(match.group(1))
    else:
        print(f"PRISM error:\n{result.stderr}")
        raise RuntimeError("Could not parse probability from PRISM output.")

    if cache is not None:
        cache[current_state_idx] = prob

    os.remove(tmp_path)
    return prob


def monitor_trace(trace, predicates, dtmc_path, model, unsafe_indices,
                  threshold=0.9, bound=-1, downsample=100):
    state_idx = model["state_index"]
    pctl = build_pctl(unsafe_indices, bound)
    cache = {}
    alerts = []

    bound_str = f"<={bound} steps" if bound > 0 else "unbounded"
    print(f"\nMonitoring {len(trace)} steps (downsample={downsample}), "
          f"threshold={threshold}, bound={bound_str}")
    print(f"Unsafe state indices: {unsafe_indices}")
    print("-" * 70)

    for i in range(0, len(trace), downsample):
        obs = trace[i]
        s = encode(obs, predicates)

        if s not in state_idx:
            print(f"Step {i:>6}: state={s} (unobserved in training data, skipping)")
            continue

        s_idx = int(state_idx[s])
        prob = check_reachability(dtmc_path, s_idx, pctl, cache)

        alert = " << ALERT" if prob >= threshold else ""
        print(f"Step {i:>6}: state={s} (idx={s_idx}), "
              f"speed={obs.get('speed', 0):.1f}, "
              f"P(unsafe)={prob:.4f}{alert}")

        if prob >= threshold:
            alerts.append({"step": i, "state": s, "probability": prob})

    print("-" * 70)
    if alerts:
        print(f"ALERTS: {len(alerts)} steps exceeded threshold {threshold}")
    else:
        print("No alerts triggered.")
    return alerts


def main():
    parser = argparse.ArgumentParser(description="Runtime monitoring with learned DTMC")
    parser.add_argument("trace_file", help="JSON trace file (with 'trajectory' key)")
    parser.add_argument("--dtmc", required=True, help="Path to dtmc.prism file")
    parser.add_argument("--model", required=True, help="Path to model.json file")
    parser.add_argument("--predicates", required=True,
                        choices=sorted(PREDICATE_SETS.keys()),
                        help="Predicate set (must match the one used for learning)")
    parser.add_argument("--threshold", type=float, default=0.9,
                        help="Alert threshold for P(reaching unsafe)")
    parser.add_argument("--bound", type=int, default=-1,
                        help="Bounded reachability (number of steps, -1 for unbounded)")
    parser.add_argument("--downsample", type=int, default=100,
                        help="Check every Nth step")
    parser.add_argument("--unsafe", type=str, default=None,
                        help="Comma-separated unsafe state indices "
                             "(default: collision states)")
    args = parser.parse_args()

    # Load model
    with open(args.model) as f:
        model = json.load(f)

    # Load trace
    with open(args.trace_file) as f:
        data = json.load(f)
    trace = data["trajectory"]

    predicates = PREDICATE_SETS[args.predicates]
    states = model["states"]
    state_idx = model["state_index"]

    # Determine unsafe states
    if args.unsafe:
        unsafe_indices = [int(x) for x in args.unsafe.split(",")]
    else:
        unsafe_indices = find_unsafe_states(states, state_idx)
        if not unsafe_indices:
            print("No collision states found in model. "
                  "Use --unsafe to specify unsafe state indices.")
            print(f"Available states: {list(enumerate(states))}")
            return

    monitor_trace(trace, predicates, args.dtmc, model, unsafe_indices,
                  threshold=args.threshold, bound=args.bound,
                  downsample=args.downsample)


if __name__ == "__main__":
    main()
