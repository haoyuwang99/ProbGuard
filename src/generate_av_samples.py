"""
Generate synthetic autonomous vehicle trajectory samples for DTMC building.
These are in the lawbreaker API format expected by safereach/autonomous_vehicle/build.py.

Usage:
    cd src/
    python3 generate_av_samples.py
"""

import os
import json
import random
import math

# Scenario definitions matching scenario_law_map in abstraction.py
# Each scenario has driving conditions that test specific traffic rules
SCENARIO_CONFIGS = {
    "s1": {
        "description": "Yellow light scenarios (rule38_2)",
        "num_traces": 8,
        "trace_length": 50,
        "generate": "yellow_light",
    },
    "s2": {
        "description": "Red light stop scenarios (rule51_5)",
        "num_traces": 8,
        "trace_length": 50,
        "generate": "red_light_stop",
    },
    "s3": {
        "description": "Green light with NPC ahead (rule38_1) + collision risk",
        "num_traces": 8,
        "trace_length": 50,
        "generate": "green_light_npc",
    },
    "s4": {
        "description": "Red light at junction (rule51_5)",
        "num_traces": 8,
        "trace_length": 50,
        "generate": "red_light_junction",
    },
    "s5": {
        "description": "Red light stop (rule51_5)",
        "num_traces": 8,
        "trace_length": 50,
        "generate": "red_light_stop",
    },
    "s9": {
        "description": "Traffic jam scenarios (rule53)",
        "num_traces": 8,
        "trace_length": 50,
        "generate": "traffic_jam",
    },
    "s10": {
        "description": "Priority NPC/Peds turning (rule51_7)",
        "num_traces": 8,
        "trace_length": 50,
        "generate": "priority_turning",
    },
}


def make_base_step(time_s):
    """Create a base lawbreaker-API-format observation step."""
    return {
        "time": time_s,
        "gear": 1,
        "engineOn": 1,
        "direction": 0,  # 0=forward, 1=left, 2=right
        "manualIntervention": 0,
        "speed": 30.0,
        "acc": 0.0,
        "brake": 0.0,
        "isLaneChanging": 0,
        "isOverTaking": 0,
        "isTurningAround": 0,
        "currentLanenumber": 201,
        "currentLanedirection": 0,
        "speedLimitlowerLimit": 0,
        "speedLimitupperLimit": 120,
        "honkingAllowed": 1,
        "crosswalkAhead": 100,
        "junctionAhead": 100,
        "stopSignAhead": 100,
        "signalAhead": 0,
        "stoplineAhead": 100,
        "streetLightOn": 0,
        "specialLocationAheadlocation": 0,
        "specialLocationAheadtype": 0,
        "trafficLightAheadcolor": 3,  # GREEN
        "trafficLightAheadblink": 0,
        "PriorityNPCAhead": 0,
        "PriorityPedsAhead": 0,
        "isTrafficJam": 0,
        "NPCAheadAhead": 1000,
        "NPCAheadspeed": 0,
        "NearestNPCAhead": 1000,
        "NearestNPCspeed": 0,
        "NPCOppositeAhead": 1000,
        "NPCOppositespeed": 0,
        "rain": 0,
        "snow": 0,
        "fog": 0,
        "trafficLightAheadArrowDirectioncolor": 3,
        "trafficLightAheadArrowDirectionblink": 0,
        "visibility": 100,
        "collision": 0,
        "reach_destination": 0,
        "fit_score": {},
    }


def gen_yellow_light(trace_length, variant=0):
    """Generate a trajectory for yellow light scenario (rule38_2).
    Vehicle approaches intersection, light turns yellow, must decide to stop or proceed.
    """
    traj = []
    # Variant controls behavior: 0=safe stop, 1=safe proceed, 2=unsafe(run through)
    for i in range(trace_length):
        step = make_base_step(i * 0.1)
        t = i / trace_length

        if t < 0.3:
            # Approaching intersection, green light
            step["trafficLightAheadcolor"] = 3
            step["speed"] = 30 + random.gauss(0, 2)
            step["stoplineAhead"] = max(0, 50 * (1 - t / 0.3))
            step["signalAhead"] = 1
        elif t < 0.5:
            # Light turns yellow
            step["trafficLightAheadcolor"] = 2
            step["signalAhead"] = 1
            step["stoplineAhead"] = max(0, 50 * (1 - t / 0.3))
            if variant == 0:
                # Braking to stop (in lane > 0)
                step["currentLanenumber"] = 201
                step["speed"] = max(0, 30 * (1 - (t - 0.3) / 0.2))
                step["brake"] = 50
            elif variant == 1:
                # Already past stop line (lane == 0), proceed
                step["currentLanenumber"] = 0
                step["speed"] = 25 + random.gauss(0, 2)
            else:
                # Running yellow at high speed
                step["currentLanenumber"] = 201
                step["speed"] = 35 + random.gauss(0, 2)
        elif t < 0.7:
            # Light is red now
            step["trafficLightAheadcolor"] = 1
            step["signalAhead"] = 1
            step["stoplineAhead"] = max(0, 5 * (1 - (t - 0.5) / 0.2))
            if variant == 0:
                step["speed"] = max(0, 5 * (1 - (t - 0.5) / 0.1))
                step["currentLanenumber"] = 201
            elif variant == 1:
                step["speed"] = 20 + random.gauss(0, 2)
                step["currentLanenumber"] = 0
            else:
                step["speed"] = 30 + random.gauss(0, 2)
                step["currentLanenumber"] = 201
        else:
            # After intersection
            step["trafficLightAheadcolor"] = 1
            step["signalAhead"] = 0
            if variant == 0:
                step["speed"] = 0
                step["currentLanenumber"] = 201
            else:
                step["speed"] = 25 + random.gauss(0, 2)
                step["currentLanenumber"] = 201

            if t > 0.95:
                step["reach_destination"] = 1

        step["speed"] = max(0, step["speed"])
        step["fit_score"] = {"rule38_2": 1.0 if step["speed"] < 0.5 or step["trafficLightAheadcolor"] != 2 or step["currentLanenumber"] == 0 else 0.5}
        traj.append(step)
    return traj


def gen_red_light_stop(trace_length, variant=0):
    """Generate trajectory for red light stop scenario (rule51_5)."""
    traj = []
    for i in range(trace_length):
        step = make_base_step(i * 0.1)
        t = i / trace_length

        if t < 0.4:
            step["trafficLightAheadcolor"] = 3
            step["speed"] = 30 + random.gauss(0, 2)
            step["stoplineAhead"] = max(0, 80 * (1 - t / 0.4))
            step["signalAhead"] = 1
        elif t < 0.6:
            step["trafficLightAheadcolor"] = 1  # RED
            step["signalAhead"] = 1
            step["stoplineAhead"] = max(0, 10 * (1 - (t - 0.4) / 0.2))
            if variant == 0:
                step["speed"] = max(0, 30 * (1 - (t - 0.4) / 0.15))
                step["brake"] = 60
            else:
                step["speed"] = 20 + random.gauss(0, 3)
        else:
            step["trafficLightAheadcolor"] = 1
            step["signalAhead"] = 1
            step["stoplineAhead"] = 0.5
            if variant == 0:
                step["speed"] = random.uniform(0, 0.3)
            else:
                step["speed"] = max(0, 5 * (1 - (t - 0.6) / 0.2)) + random.gauss(0, 1)

            if t > 0.9:
                step["trafficLightAheadcolor"] = 3
                step["speed"] = 15 + random.gauss(0, 2)

            if t > 0.95:
                step["reach_destination"] = 1

        step["speed"] = max(0, step["speed"])
        step["fit_score"] = {"rule51_5": 1.0}
        traj.append(step)
    return traj


def gen_green_light_npc(trace_length, variant=0):
    """Generate trajectory for green light with NPC ahead (rule38_1)."""
    traj = []
    for i in range(trace_length):
        step = make_base_step(i * 0.1)
        t = i / trace_length

        step["trafficLightAheadcolor"] = 3
        step["signalAhead"] = 1

        if t < 0.3:
            step["speed"] = 30 + random.gauss(0, 2)
            step["NPCAheadAhead"] = 50 - t * 100
        elif t < 0.6:
            step["NPCAheadAhead"] = max(2, 20 - (t - 0.3) * 60)
            step["NPCAheadspeed"] = 10 + random.gauss(0, 2)
            if variant == 0:
                step["speed"] = max(5, 20 - (t - 0.3) * 30)
            else:
                step["speed"] = 25 + random.gauss(0, 2)
                if variant == 2 and t > 0.5:
                    step["collision"] = 1
        else:
            step["NPCAheadAhead"] = 15 + random.gauss(0, 3)
            step["NPCAheadspeed"] = 20 + random.gauss(0, 3)
            step["speed"] = 20 + random.gauss(0, 2)
            if t > 0.95:
                step["reach_destination"] = 1

        step["speed"] = max(0, step["speed"])
        step["fit_score"] = {"rule38_1": 1.0}
        traj.append(step)
    return traj


def gen_red_light_junction(trace_length, variant=0):
    """Red light at junction (rule51_5 + rule44)."""
    traj = []
    for i in range(trace_length):
        step = make_base_step(i * 0.1)
        t = i / trace_length

        if t < 0.3:
            step["trafficLightAheadcolor"] = 3
            step["speed"] = 35 + random.gauss(0, 2)
            step["junctionAhead"] = max(0, 60 * (1 - t / 0.3))
            step["signalAhead"] = 1
        elif t < 0.5:
            step["trafficLightAheadcolor"] = 1
            step["signalAhead"] = 1
            step["junctionAhead"] = max(0, 5 * (1 - (t - 0.3) / 0.2))
            if variant == 0:
                step["speed"] = max(0, 35 * (1 - (t - 0.3) / 0.15))
                step["brake"] = 70
            else:
                step["speed"] = 20 + random.gauss(0, 2)
        else:
            step["trafficLightAheadcolor"] = 3 if t > 0.8 else 1
            step["signalAhead"] = 1
            if variant == 0 and t < 0.8:
                step["speed"] = random.uniform(0, 0.3)
            else:
                step["speed"] = 20 + random.gauss(0, 2)
            if t > 0.95:
                step["reach_destination"] = 1

        step["speed"] = max(0, step["speed"])
        step["fit_score"] = {"rule51_5": 1.0, "rule44": 1.0}
        traj.append(step)
    return traj


def gen_traffic_jam(trace_length, variant=0):
    """Traffic jam scenario (rule53)."""
    traj = []
    for i in range(trace_length):
        step = make_base_step(i * 0.1)
        t = i / trace_length

        if t < 0.2:
            step["speed"] = 30 + random.gauss(0, 2)
            step["isTrafficJam"] = 0
        elif t < 0.7:
            step["isTrafficJam"] = 1
            step["NPCAheadAhead"] = random.uniform(0.3, 5)
            step["NPCAheadspeed"] = random.uniform(0, 0.3)
            step["junctionAhead"] = random.uniform(0, 2)
            if variant == 0:
                step["speed"] = max(0, 10 * (1 - (t - 0.2) / 0.3))
                step["brake"] = 40
            else:
                step["speed"] = 5 + random.gauss(0, 2)
        else:
            step["isTrafficJam"] = 0
            step["speed"] = 15 + (t - 0.7) * 50
            step["NPCAheadAhead"] = 30 + random.gauss(0, 5)
            if t > 0.95:
                step["reach_destination"] = 1

        step["speed"] = max(0, step["speed"])
        step["fit_score"] = {"rule53": 1.0}
        traj.append(step)
    return traj


def gen_priority_turning(trace_length, variant=0):
    """Priority NPC/Peds turning scenario (rule51_7)."""
    traj = []
    for i in range(trace_length):
        step = make_base_step(i * 0.1)
        t = i / trace_length

        step["direction"] = 1 if t > 0.3 else 0  # turning left

        if t < 0.3:
            step["speed"] = 25 + random.gauss(0, 2)
        elif t < 0.5:
            step["PriorityNPCAhead"] = 1
            step["direction"] = 2
            if variant == 0:
                step["speed"] = max(0, 20 * (1 - (t - 0.3) / 0.15))
                step["brake"] = 50
            else:
                step["speed"] = 15 + random.gauss(0, 2)
        elif t < 0.7:
            step["PriorityPedsAhead"] = 1
            step["direction"] = 1
            if variant == 0:
                step["speed"] = random.uniform(0, 0.3)
            else:
                step["speed"] = 8 + random.gauss(0, 2)
        else:
            step["direction"] = 0
            step["speed"] = 20 + random.gauss(0, 2)
            if t > 0.95:
                step["reach_destination"] = 1

        step["speed"] = max(0, step["speed"])
        step["fit_score"] = {"rule51_7": 1.0}
        traj.append(step)
    return traj


GENERATORS = {
    "yellow_light": gen_yellow_light,
    "red_light_stop": gen_red_light_stop,
    "green_light_npc": gen_green_light_npc,
    "red_light_junction": gen_red_light_junction,
    "traffic_jam": gen_traffic_jam,
    "priority_turning": gen_priority_turning,
}


def main():
    samples_dir = os.path.join(os.path.dirname(__file__), "safereach", "autonomous_vehicle", "samples")
    tests_dir = os.path.join(os.path.dirname(__file__), "safereach", "autonomous_vehicle", "tests")

    for scenario, config in SCENARIO_CONFIGS.items():
        gen_func = GENERATORS[config["generate"]]

        # Generate samples (for build.py)
        scenario_sample_dir = os.path.join(samples_dir, scenario)
        os.makedirs(scenario_sample_dir, exist_ok=True)

        for i in range(config["num_traces"]):
            variant = i % 3  # cycle through variants
            traj = gen_func(config["trace_length"], variant=variant)
            sample = {"trajectory": traj}
            with open(os.path.join(scenario_sample_dir, f"trace_{i:05d}.json"), "w") as f:
                json.dump(sample, f)

        # Generate test traces (for av_monitor.py)
        scenario_test_dir = os.path.join(tests_dir, scenario)
        os.makedirs(scenario_test_dir, exist_ok=True)

        for i in range(3):
            variant = i % 3
            traj = gen_func(config["trace_length"], variant=variant)
            sample = {"trajectory": traj}
            with open(os.path.join(scenario_test_dir, f"test_{i:05d}.json"), "w") as f:
                json.dump(sample, f)

        print(f"{scenario}: {config['num_traces']} samples + 3 tests ({config['description']})")

    print(f"\nSamples saved to: {samples_dir}")
    print(f"Tests saved to: {tests_dir}")
    print("\nYou can now build DTMCs with:")
    print("  python3 -m safereach.autonomous_vehicle.build")


if __name__ == "__main__":
    main()
