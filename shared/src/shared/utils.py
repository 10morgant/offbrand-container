import yaml

from shared.classes import Registry


def read_registries(file: str = "registries.yaml") -> list[Registry] | None:
    with open(file, "r") as f:
        data = yaml.safe_load(f)

        registries = [
            Registry(**fields)
            for _, fields in data["registries"].items()
        ]
        return registries
    return None
