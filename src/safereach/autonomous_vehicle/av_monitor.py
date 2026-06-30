import os
import json 
import pickle
from .abstraction import convert_to_bool_var,AVAbstraction, REACH, COLLISION, scenario_law_map
from ..runtime_monitor import runtime_monitor
from .TracePreprocess import raw_to_lawbreaker_API
from .law import *
from ..predicate import *
 
def load_abstraction(abstraction_desc_path):
    with open(abstraction_desc_path) as f:
        obj = json.load(f)
        rule = obj["rule"]
    return AVAbstraction(rule)

BOUNDED_RESPONSE = "bound"
LAW_VIOLATION_PREDICATE = "law"
LOG_BASE = os.path.join(os.path.dirname(__file__), 'tests') + '/'
DTMC_BASE = "safereach/dtmcs/"

unsafe_predicates = {
    "s1": LAW_VIOLATION_PREDICATE,
    "s2": LAW_VIOLATION_PREDICATE,
    "s3": COLLISION,
    "s4": LAW_VIOLATION_PREDICATE,
    "s5": LAW_VIOLATION_PREDICATE,
    "s6": LAW_VIOLATION_PREDICATE,
    "s7": LAW_VIOLATION_PREDICATE,
    "s8": COLLISION,
    "s9": LAW_VIOLATION_PREDICATE,
    "s10": LAW_VIOLATION_PREDICATE,
}

# s6 and s7 violates law at the first timeframe??

# abs = load_abstraction(abs_path)
# unsafe_states = abs.filter()
# unsafe_states = [abs.get_state_idx()[state] for state in list(unsafe_states)]

#interp: propositions in the form of {(lhs, op, rhs): bool_val ...}
# it returns the value of the predicate.
def truth_table(interp, pred):
    if type(pred)==AtomicPredicate:
        
        pred_name = convert_to_bool_var(pred.lhs, pred.op, pred.rhs)
        pred_value = interp[pred_name]
        return pred_value
    elif type(pred) == BinaryPredicate:
        if pred.op == "and":
            return truth_table(interp, pred.lhs) and truth_table(interp, pred.rhs) 
        else:
            return truth_table(interp, pred.lhs) or truth_table(interp, pred.rhs) 
    else:
        raise Exception("Unsupported type")
    
# this returns the states that satisfy the pred
def filter(state_interp, pred):

    states = []
    for s in state_interp:
        if truth_table(state_interp[s], pred):
            states.append(s)
    return states

for scenario in os.listdir(LOG_BASE):
    LOGDIR = f"{LOG_BASE}{scenario}/"
    if scenario in ["s6","s7"]:
        continue
    rule = scenario_law_map[scenario][0]
    abs = AVAbstraction(rule)
    model_path = f"{DTMC_BASE}{scenario}/dtmc.prism"
    model_des = f"{DTMC_BASE}{scenario}/model.json"
    with open(model_des) as f:
        obj = json.loads(f.read())
        state_idx = obj["state_index"]
        state_interp = obj["state_interpret"]
        unobserved_state = len(state_idx.keys())
        
    cache = {}
    
    predicate = unsafe_predicates[scenario]
    if predicate == COLLISION: 
        continue
        print(LOGDIR)
        # print(COLLISION)
        unsafe_states = filter(state_interp, COLLISION )
        unsafe_states = [state_idx[state] for state in list(unsafe_states)]
        
        print(unsafe_states)
    else :
        # 1. parse varphi_s, varphi_t and K from the rule
        components = [] #(predicate s, predicate t, K)
        for imply in abs.implies:
            pre = convert(imply[0])
            print(pre)
            
        print(rule)
        
    continue
    violated_and_detected = 0
    ahead = 0
    for log in os.listdir(LOGDIR):
        if log.find("00000") == -1:
            continue
        if not log.endswith(".json"):
            continue 
        
        traj = []
        with open(f"{LOGDIR}{log}") as f:
            traj = json.load(f)["trajectory"]
        
        nexts = [ o for o in os.listdir(LOGDIR)\
            if o.startswith(log[:log.find(".")]) and o.find("00000")==-1 and o.endswith("json")]
        for n in nexts:
            with open(f"{LOGDIR}{n}") as f:
                traj.extend(json.load(f)["trajectory"])
                
        t_event = {} # maps t1 to lexpr
            
        total_time = traj[-1]["time"]
        violation_time = -1
        violated = False
        monitor_time = -1
        monitored = False
        for step in traj: 
            fit_score = float(step["fit_score"][rule])
            step["fit_score"] = {
                rule: 1.0
            }
            if not monitored:
                try :
                    # translate the STL formula to PCTL (which depends on runtime information)
                    prob = runtime_monitor(step, model_path, abs, cache = cache)
                except:
                    break
                print(prob)
                if not prob < 0.7:
                    monitor_time = step["time"]
                    monitored = True
            if not violated:
                if predicate == COLLISION_PREDICATE and step["collision"] == 1:
                    violation_time = step["time"]
                    violated= True
                elif predicate == LAW_VIOLATION_PREDICATE and fit_score <= 0.0:
                    violation_time = step["time"]
                    violated= True
                    break
                else:
                    pass
        
        if violated:
            if monitor_time == -1:
                print("violated but not detected!")
            else:
                
                violated_and_detected = violated_and_detected + 1
                ahead = ahead + violation_time - monitor_time
        print(f"monitor_time: {monitor_time}")
        print(f"violation_time: {violation_time}")
        # print(f"total_time: {total_time}")
        
    if violated_and_detected==0:
        violated_and_detected = 1
    print(f"{scenario}, {ahead/violated_and_detected}")


# print(unsafe_states)
# # exit(1)
# for f in os.listdir(LOG_DIR):
    # if not f.endswith("pickle"):
    #     continue
    # with open(f"{LOG_DIR}{f}", 'rb') as pic:
    #     trace = pickle.load(pic)["trace"]

    #     time_seq = sorted(list(trace.keys()))
    #     if len(trace.keys()) == 0:
    #         continue
    #     initial_timestamp = time_seq[0]
    #     enforced_trace = []

    #     cache = {}
    #     for i in range(len(time_seq)):
    #         if i%100 == 0:
    #             print(i)
    #         step = trace[time_seq[i]]
    #         observation = raw_to_lawbreaker_API(step, initial_timestamp)
    #         # s_idx = abs.get_state_idx()[abs.encode(observation)]

    #         prob = runtime_monitor(observation, dtmc_path, abs, set(unsafe_states), cache = cache)
    #         # # print(prob)
    #         # if prob < 0.05:
    #         #     print(i)
    #             # print(len(trace))
    #     print(cache)
    #     exit(0)
# with open()