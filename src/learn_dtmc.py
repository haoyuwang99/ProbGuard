"""
Learn a DTMC from a set of AV traces and predefined predicates.

Usage:
    python3 learn_dtmc.py /tmp/av_traces/ --out dtmc_out/ --num_traces 10
"""

import os
import json
import glob
import argparse
import operator
from fractions import Fraction
from collections import defaultdict

# ── Predicate definition ──────────────────────────────────────────────

OP = {
    "==": operator.eq, "!=": operator.ne,
    ">":  operator.gt, "<":  operator.lt,
    ">=": operator.ge, "<=": operator.le,
}

class Predicate:
    def __init__(self, var, op, val):
        self.var = var
        self.op = op
        self.val = float(val)
        self._fn = OP[op]

    def eval(self, obs):
        return self._fn(float(obs[self.var]), self.val)

    def __repr__(self):
        return f"{self.var} {self.op} {self.val}"


# ── Example predicate sets (pick one or define your own) ──────────────

PREDICATE_SETS = {
    "traffic_light": [
        Predicate("trafficLightAheadcolor", "==", 1),   # red
        Predicate("trafficLightAheadcolor", "==", 2),   # yellow
        Predicate("speed", ">", 0.5),                   # moving
        Predicate("speed", "<", 0.5),                    # stopped
    ],
    "npc_interaction": [
        Predicate("NPCAheadAhead", "<=", 8),             # NPC close ahead
        Predicate("speed", ">", 0.5),                    # moving
        Predicate("speed", "<", 0.5),                    # stopped
        Predicate("PriorityNPCAhead", "==", 1),          # priority NPC
    ],
    "junction": [
        Predicate("junctionAhead", "<=", 2),             # near junction
        Predicate("trafficLightAheadcolor", "==", 1),    # red
        Predicate("speed", ">", 0.5),                    # moving
        Predicate("speed", "<", 0.5),                    # stopped
    ],
    "pedestrian_npc": [
        Predicate("NPCAheadAhead", "<=", 50),            # NPC within 50m
        Predicate("NearestNPCAhead", "<=", 20),          # nearest NPC close
        Predicate("speed", ">", 2.0),                    # cruising
        Predicate("isLaneChanging", "==", 1),             # lane changing
    ],
}

# Terminal states
COLLISION = Predicate("collision", "==", 1)
REACH     = Predicate("reach_destination", "==", 1)


# ── Abstraction: observations → bitstring ─────────────────────────────

def encode(obs, predicates):
    """Encode an observation into a bitstring: collision|reach|pred1|pred2|..."""
    if COLLISION.eval(obs):
        return "10" + "0" * len(predicates)
    if REACH.eval(obs):
        return "01" + "0" * len(predicates)
    bits = "00"
    for p in predicates:
        bits += "1" if p.eval(obs) else "0"
    return bits


def is_absorbing(state):
    return state.startswith("1") or state.startswith("01")


# ── DTMC learning ─────────────────────────────────────────────────────

def learn_dtmc(traces, predicates, alpha=1.0):
    """
    Learn a DTMC from traces.
      traces: list of lists of observation dicts
      predicates: list of Predicate
      alpha: Laplace smoothing parameter
    Returns (states, transition_probs, state_index)
    """
    # 1. Encode all traces → state sequences
    state_seqs = []
    state_space = set()
    for traj in traces:
        seq = []
        for obs in traj:
            s = encode(obs, predicates)
            seq.append(s)
            state_space.add(s)
        state_seqs.append(seq)

    states = sorted(state_space)
    K = len(states)
    idx = {s: i for i, s in enumerate(states)}

    # 2. Count transitions
    counts = [[0] * K for _ in range(K)]
    for seq in state_seqs:
        for t in range(len(seq) - 1):
            i, j = idx[seq[t]], idx[seq[t + 1]]
            counts[i][j] += 1

    # 3. Compute probabilities with Laplace smoothing
    transition_probs = {}
    for i, s_from in enumerate(states):
        row = {}
        denom = 0
        entries = []
        for j, s_to in enumerate(states):
            can_reach = not is_absorbing(s_from)
            c = counts[i][j]
            smooth = alpha if can_reach else 0
            entries.append((j, c + smooth))
            denom += c + smooth
        if denom > 0:
            row = {j: Fraction(n).limit_denominator(10000)
                   for j, n in entries if n > 0}
            # Normalize
            total = sum(row.values())
            row = {j: f"{Fraction(v, total).limit_denominator(10000)}"
                   for j, v in row.items()}
        else:
            row = {i: "1"}
        transition_probs[i] = row

    return states, transition_probs, idx


# ── Output ────────────────────────────────────────────────────────────

def write_prism(states, probs, path):
    K = len(states)
    with open(path, "w") as f:
        f.write("dtmc\n\nmodule dtmc_model\n\n")
        f.write(f"    s : [0..{K - 1}] init 0;\n\n")
        for i in range(K):
            row = probs.get(i, {i: "1"})
            parts = [f"{p} : (s'={j})" for j, p in row.items()]
            f.write(f"    [] s={i} -> {' + '.join(parts)};\n")
        f.write("\nendmodule\n")


def write_model_json(states, probs, predicates, path):
    idx = {s: i for i, s in enumerate(states)}

    # Decode state interpretation
    state_interp = {}
    for s in states:
        interp = {"collision": s[0] == "1", "reach": s[1] == "1"}
        for k, p in enumerate(predicates):
            interp[repr(p)] = s[2 + k] == "1"
        state_interp[s] = interp

    model = {
        "states": states,
        "state_index": idx,
        "state_interpret": {s: interp for s, interp in state_interp.items()},
        "transition_probs": {i: row for i, row in probs.items()},
        "predicates": [repr(p) for p in predicates],
    }
    with open(path, "w") as f:
        json.dump(model, f, indent=2, default=str)


def print_summary(states, probs, predicates):
    print(f"\nPredicates ({len(predicates)}):")
    for i, p in enumerate(predicates):
        print(f"  bit[{i}]: {p}")
    print(f"\nStates: {len(states)}")
    print(f"  collision state: 10{'0' * len(predicates)}")
    print(f"  reach state:     01{'0' * len(predicates)}")

    # Show top transitions from initial states
    observed = [s for s in states if not is_absorbing(s)]
    print(f"  driving states:  {len(observed)}")
    print(f"\nSample transitions (from most common states):")
    for s_idx in list(probs.keys())[:5]:
        row = probs[s_idx]
        top = sorted(row.items(), key=lambda x: -float(Fraction(x[1])))[:3]
        top_str = ", ".join(f"s{j}({p})" for j, p in top)
        print(f"  s{s_idx} [{states[s_idx]}] -> {top_str}")


# ── Main ──────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="Learn DTMC from AV traces")
    parser.add_argument("trace_dir", help="Directory with trace JSON files")
    parser.add_argument("--out", default="dtmc_out", help="Output directory")
    parser.add_argument("--num_traces", type=int, default=10, help="Number of traces to use")
    parser.add_argument("--predicates", default="traffic_light",
                        choices=sorted(PREDICATE_SETS.keys()),
                        help="Predicate set to use")
    parser.add_argument("--alpha", type=float, default=1.0, help="Laplace smoothing")
    parser.add_argument("--downsample", type=int, default=100,
                        help="Take every Nth step (traces can be very long)")
    args = parser.parse_args()

    # Load traces
    files = sorted(glob.glob(os.path.join(args.trace_dir, "*.json")))[:args.num_traces]
    if not files:
        print(f"No JSON files found in {args.trace_dir}")
        return

    predicates = PREDICATE_SETS[args.predicates]
    traces = []
    for fp in files:
        with open(fp) as f:
            data = json.load(f)
        traj = data["trajectory"][::args.downsample]  # downsample
        traces.append(traj)
        print(f"  Loaded {os.path.basename(fp)}: {len(data['trajectory'])} steps -> {len(traj)} sampled")

    print(f"\nLearning DTMC from {len(traces)} traces with '{args.predicates}' predicates...")
    states, probs, idx = learn_dtmc(traces, predicates, alpha=args.alpha)

    os.makedirs(args.out, exist_ok=True)
    write_prism(states, probs, os.path.join(args.out, "dtmc.prism"))
    write_model_json(states, probs, predicates, os.path.join(args.out, "model.json"))

    print_summary(states, probs, predicates)
    print(f"\nOutput written to {args.out}/")
    print(f"  dtmc.prism   - PRISM model file")
    print(f"  model.json   - Full model with state interpretations")


if __name__ == "__main__":
    main()
