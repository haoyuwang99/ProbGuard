import os
import json
from ..build_model import *
from .abstraction import EmbodiedAbstraction
from ..predicate import *

def embodied_build_model(dir, model_path, alpha=1.0):  
    
    if not os.path.exists( dir + "/spec"):
        # os.system(f"mv {dir} samples/embodied_no_final_state")
        return
    logs = []
    for f in os.listdir(dir):
        if not f.endswith("json"):
            continue
        with open( dir + "/" + f) as f:
            obj = json.loads(f.read())
            log = [o["state"] for o in obj["s_trans"]]
            log.append(FINISH)
            logs.append(log)

    specs = []
    with open(dir + "/spec") as f:
        specs = json.loads(f.read()) 
    try: 
        # define abstraction level
        OTY = "objectType"
        PR = "parentReceptacles"
        abs_predicates = []
        for spec in specs:
            preds = []
            for key in spec: 
                if key == OTY:
                    obj_pred = AtomicPredicate(lhs=OTY, op="==", rhs=spec[OTY])
                    preds.append(obj_pred)
                elif key == PR:
                    if len(spec[PR])==1:
                        preds.append(AtomicPredicate(lhs=PR, op="==", rhs=spec[PR]))
                else:
                    preds.append(AtomicPredicate(lhs=key, op="==", rhs=True))
            conjunction_pred = None
            for pred in preds:
                abs_predicates.append(QuantifiedPredicate(quantifier="exist", predicate = pred))
                if conjunction_pred == None:
                    conjunction_pred = pred
                else:
                    conjunction_pred = BinaryPredicate(lhs=conjunction_pred, op="and", rhs=pred)
            abs_predicates.append(QuantifiedPredicate(quantifier="exist", predicate=conjunction_pred))        
        # print(specs)
        # print(abs_predicates)
        # print("====")
        abstraction = EmbodiedAbstraction(abs_predicates)
        model = build_model(logs, abstraction, alpha)
        if not os.path.exists(model_path):
            os.mkdir(model_path)
        store_model(model, model_path, abstraction)
        
    except Exception as e:
        
        raise e

LOG_DIR = os.path.join(os.path.dirname(__file__), 'merged_sample') + '/'
MODEL_DIR = 'safereach/dtmcs/embodied/'
log_dirs = [f for f in os.listdir(LOG_DIR) if f.startswith('log_raw_t') and not f.endswith("jsonl")]
for dir in log_dirs : 
    # if not dir.find("11") !=-1:
    #     continue
    model = MODEL_DIR + "merged_" + dir + "/"
    dir = LOG_DIR + dir + "/"
    try: 
        print(dir)
        embodied_build_model(dir, model) 
        # break
    except Exception as e: 
        # raise e
        if str(e).startswith("global"):
            raise e
        print(e)