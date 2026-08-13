from dataclasses import dataclass


@dataclass
class Registry:
    display_name: str
    url: str
    self_hosted: bool