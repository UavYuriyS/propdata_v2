#  "THE BEER-WARE LICENSE" (Revision 42):
#
#  <y.sukhorukov.uav@gmail.com> wrote this file.
#  As long as you retain this notice you can do whatever you want with this stuff.
#  If we meet some day, and you think this stuff is worth it, you can buy me a beer in return.
#  Yuriy Sukhorukov

from __future__ import annotations
from dataclasses import dataclass
from pathlib import Path
from typing import Literal, Optional

import dacite
import yaml

from models import Columns


@dataclass
class ConstraintEntry:
    name: Literal["power", "torque", "rpm", "dia"]
    low: Optional[float]
    high: Optional[float]

    def does_match(self, value: float):
        return  (self.low is None or self.low <= value) and (self.high is None or value <= self.high)


@dataclass
class ConstraintPoint:
    name: str
    entries: list[ConstraintEntry]

    def does_match(self, constraint_data: dict[str, float]):
        return all(map(lambda x: x.does_match(constraint_data[x.name]), self.entries))

@dataclass
class ConditionEntry:
    name: str
    airspeed: float
    thrust: float = None
    weight: float = 1.0
    input: Columns | Literal["rpm"] = None
    input_value: float = None

@dataclass
class ConstraintConfig:
    constraints: list[ConstraintPoint]
    conditions: list[ConditionEntry]

    def does_match(self, constraint_data: dict[str, float]):
        return all(map(lambda x: x.does_match(constraint_data), self.constraints))


    @staticmethod
    def load_config(config_path: Path) -> ConstraintConfig:
        with open(config_path) as f:
            config_data = yaml.safe_load(f)
        conf = dacite.Config()
        return dacite.from_dict(data_class=ConstraintConfig, data=config_data, config=conf)