#  "THE BEER-WARE LICENSE" (Revision 42):
#
#  <y.sukhorukov.uav@gmail.com> wrote this file.
#  As long as you retain this notice you can do whatever you want with this stuff.
#  If we meet some day, and you think this stuff is worth it, you can buy me a beer in return.
#  Yuriy Sukhorukov

from dataclasses import dataclass, field
from enum import Enum

from numpy import ndarray


class Columns(Enum):
    AIRSPEED      = 0
    ADV_RATIO     = 1
    PROP_EFF      = 2
    THRUST_COEFF  = 3
    POWER_COEFF   = 4
    POWER         = 8
    TORQUE        = 9
    THRUST        = 10
    THRUST_TO_PWR = 11
    MACH          = 12
    RE            = 13
    FOM           = 14

@dataclass
class Prop:
    name: str
    link: str
    dia: float = 0
    pitch: float = 0
    matrices: dict[Columns, ndarray] = field(init=False)
    rpms: ndarray = field(init=False)