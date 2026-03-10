import os
import yaml

class Config:
    def __init__(self, config_path="config.yaml"):
        self.config_path = config_path
        self.data = self.load_config()

    def load_config(self):
        if os.path.exists(self.config_path):
            with open(self.config_path, "r") as f:
                return yaml.safe_load(f)
        return {}

    def get(self, key, default=None):
        return self.data.get(key, default)

# Example usage:
# config = Config()
# endpoint = config.get("CLU_ENDPOINT")
# key = config.get("CLU_KEY")
# ...
