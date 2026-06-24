import yaml
import os

class LLMRouter:
    def __init__(self, config_path="config/models.yml"):
        # Check if the config file exists
        if not os.path.exists(config_path):
            raise FileNotFoundError(f"Configuration file not found at: {config_path}. Please create it.")

        with open(config_path, 'r') as f:
            config = yaml.safe_load(f)
            if 'model_routing' not in config:
                raise KeyError("Key 'model_routing' not found in the configuration file.")
            self.routing_map = config['model_routing']

    def select(self, task_type: str) -> str:
        """Selects LLM based on external configuration file."""
        return self.routing_map.get(task_type, self.routing_map['default'])
