import os
import yaml
from datetime import datetime

class DataStore:
    """
    Abstract datastore interface for FDE Memory.
    Provides persistence for client profiles, configuration constraints, and decision logs.
    Resolves the base directory relative to the repository / workspace root to prevent fragmentation.
    """
    def __init__(self, base_dir=None):
        if base_dir:
            self.base_dir = base_dir
        else:
            # Auto-locate workspace root by looking for fde-skills or current working directory
            cwd = os.getcwd()
            self.base_dir = os.path.join(cwd, ".fde-memory")
            
        os.makedirs(self.base_dir, exist_ok=True)
        self.clients_dir = os.path.join(self.base_dir, "clients")
        os.makedirs(self.clients_dir, exist_ok=True)

    def sanitize_client_name(self, client_name: str) -> str:
        safe_name = "".join(c for c in client_name if c.isalnum() or c in ('-', '_')).strip().lower()
        if not safe_name:
            raise ValueError(f"Invalid client name provided: '{client_name}'")
        return safe_name

    def _get_client_path(self, client_name: str) -> str:
        safe_name = self.sanitize_client_name(client_name)
        return os.path.join(self.clients_dir, f"{safe_name}.yaml")

    def client_exists(self, client_name: str) -> bool:
        return os.path.exists(self._get_client_path(client_name))

    def list_clients(self) -> list:
        if not os.path.exists(self.clients_dir):
            return []
        clients = []
        for file in os.listdir(self.clients_dir):
            if file.endswith(".yaml"):
                full_path = os.path.join(self.clients_dir, file)
                modified_time = datetime.fromtimestamp(os.path.getmtime(full_path)).isoformat() + "Z"
                client_id = file[:-5]
                data = self.read_client(client_id)
                clients.append({
                    "client_id": client_id,
                    "name": data.get("client_name", client_id),
                    "last_modified": modified_time,
                    "decision_count": len(data.get("decisions", []))
                })
        return sorted(clients, key=lambda x: x["client_id"])

    def read_client(self, client_name: str) -> dict:
        path = self._get_client_path(client_name)
        if not os.path.exists(path):
            return {}
        try:
            with open(path, 'r', encoding='utf-8') as f:
                return yaml.safe_load(f) or {}
        except Exception as e:
            raise RuntimeError(f"Failed to read client data from {path}: {str(e)}")

    def write_client(self, client_name: str, data: dict):
        path = self._get_client_path(client_name)
        try:
            with open(path, 'w', encoding='utf-8') as f:
                yaml.dump(data, f, default_flow_style=False, sort_keys=False)
        except Exception as e:
            raise RuntimeError(f"Failed to write client data to {path}: {str(e)}")

    def update_client_keys(self, client_name: str, updates: dict) -> dict:
        data = self.read_client(client_name)
        data.update(updates)
        self.write_client(client_name, data)
        return data
