import os
import pickle
import json
from .monitor import add_timer_preprocess
from .TracePreprocess import Trace, raw_to_lawbreaker_API
from ..build_model import *
from .abstraction import AVAbstraction, scenario_law_map

def av_build_model(abs, logs, model_path = "default_av.dtmc"): 
    model = build_model(logs, abs)
    store_model(model, model_path, abs)

SAMPLES = os.path.join(os.path.dirname(__file__), 'samples') + '/'
# SCENEARIO = "safereach/autonomous_vehicle/samples/Law38_1_1/"
for s in os.listdir(SAMPLES):
    SCENEARIO = f"{SAMPLES}{s}/" 
    rule_name = scenario_law_map[s][0]
    print(SCENEARIO, ": ", rule_name)
    abs = AVAbstraction(rule_name)
    
    logs = []
    for f in os.listdir(SCENEARIO):
        if not f.endswith("json"):
            continue
        with open(f"{SCENEARIO}{f}" ) as j:
            trace = json.load(j)["trajectory"] 
            logs.append(trace)
    av_build_model(abs, logs, model_path=f"safereach/dtmcs/{s}/")
    
