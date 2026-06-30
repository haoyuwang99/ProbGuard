 ProbGuard

This is the implementation for paper `ProbGuard: Probabilistic Runtime Monitoring for LLM Agent Safety`. 


## 🚀 Get Started

* install PRISM 
```
cd prism
./install.sh
```
You can use prism at ./prism/bin/prism

* install pip dependencies:
```
pip install -r requirement.txt
```

### Learning DTMCs

#### From AV traces with predefined predicates

Use `learn_dtmc.py` to learn a DTMC from a set of AV traces with predefined predicates:

```bash
cd src/

# Learn DTMC from sample traces 
python3 learn_dtmc.py sample_traces/ \
    --predicates pedestrian_npc \
    --out dtmc_out/
```

Example predicate sets:
- `pedestrian_npc` — NPC distance (<50m, <20m), speed (>2.0), lane changing
- `traffic_light` — red/yellow light, speed (moving/stopped)
- `npc_interaction` — NPC close (<8m), speed, priority NPC
- `junction` — near junction, red light, speed

This outputs:
- `dtmc.prism` — PRISM model file
- `model.json` — full model with state interpretations

#### Example output DTMC in PRISM:
```
dtmc

module dtmc_model

    s : [0..10] init 0;

    [] s=0 -> 1/3 : (s'=0) + 2/15 : (s'=1) + 1/30 : (s'=2) + 1/5 : (s'=3) + ...;
    [] s=1 -> 1/373 : (s'=0) + 358/373 : (s'=1) + 6/373 : (s'=6) + ...;
    ...

endmodule
```

Each state is a bitstring encoding: `collision | reach | pred1 | pred2 | ...`

## Run embodied agent with runtime monitoring:
Using Langchain + [AgentSpec](https://arxiv.org/abs/2503.18666) as llm agent with runtime monitoring, equipped with low level controller (provided by [SafeAgentBench](https://github.com/shengyin1224/SafeAgentBench)).
Example: src/embodied_agent.py
```python
from agentspec.controlled_agent_excector import initialize_controlled_agent

# ...

tool = Tool(
    name="robotic controller",
    description="High-level controller for the robot.",
    func=planner.llm_skill_interact
)
tools = [tool]  # Equip LLM with low-level controller

# Initialize controlled agent with DTMC-based proactive runtime verification
agent = initialize_controlled_agent(
    tools,
    llm,
    agent="zero-shot-react-description",
    rules=[],
    abs=kwargs["abs"],
    dtmc_path=kwargs["dtmc_path"],  # Path to DTMC (output from embodied_build)
    unsafe_states=kwargs["unsafe_states"],  # Set of unsafe states (must match DTMC states)
    cache=kwargs["cache"],  # Cache to amortize DTMC inference costs
    task_obj=kwargs["task_obj"],
    threshold=kwargs["threshold"]  # Threshold for model checking (e.g., P < threshold [F unsafe_states])
)

agent.invoke(task_description)
# ...

```

## integrating ProbGuard on autonomous vehicle:

This can be achieved by generating [muDrive](https://arxiv.org/pdf/2407.13201) scripts that dynamically adjust planning settings.

## Extending ProbGuard to new Domains:

The core requirement is implementing an  `Abstraction.py` class:

```python
class Abstraction(ABC):

    # Map 01-bit strings to integer indices (as PRISM stores states)
    @abstractmethod
    def get_state_idx(self) -> Dict[str, int]:
        pass

    # Encode observations into 01-bit strings representing the state
    @abstractmethod
    def encode(self, observations: List[Any]) -> str:
        pass

    # Decode 01-bit state strings back to observation list
    @abstractmethod
    def decode(self, state: str) -> List[Any]:
        pass

    # Define valid state transitions
    @abstractmethod
    def can_reach(self, state1: str, state2: str) -> bool:
        pass

    # Return possible state bitstrings satisfying a spec (condition on observation)
    @abstractmethod
    def filter(self, spec: Any) -> Set[str]:
        pass

    # Enumerate all valid states
    @abstractmethod
    def enumerate_possible_states(self) -> Set[str]:
        pass

    
```
