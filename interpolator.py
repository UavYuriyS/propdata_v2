#  "THE BEER-WARE LICENSE" (Revision 42):
#
#  <y.sukhorukov.uav@gmail.com> wrote this file.
#  As long as you retain this notice you can do whatever you want with this stuff.
#  If we meet some day, and you think this stuff is worth it, you can buy me a beer in return.
#  Yuriy Sukhorukov

from dataclasses import dataclass
from typing import Optional

import numpy as np
from scipy.interpolate import interp1d

from config import ConditionEntry
from models import Columns, Prop

@dataclass
class PropInterpolator:
    prop: Prop
    silent: bool = False

    # Optionally add caching for interpolators but im lazy
    def evaluate_point(self, condition: ConditionEntry) -> Optional[dict[str | Columns, float]]:
        airspeed_interpolators = {}
        airspeed_interpolators: dict[Columns, list]

        # For each RPM, interpolate to find thrust and other params at the target airspeed
        for i, rpm in enumerate(self.prop.rpms):
            # Interpolate parameters
            for key, matrix in self.prop.matrices.items():
                if key not in airspeed_interpolators:
                    airspeed_interpolators[key] = []

                airspeeds = self.prop.matrices[Columns.AIRSPEED][i]
                _, unique_aspd_mask = np.unique(airspeeds, return_index=True)

                interpolator = interp1d(airspeeds[unique_aspd_mask], matrix[i][unique_aspd_mask], kind='cubic',
                                        bounds_error=False, fill_value=np.nan)
                airspeed_interpolators[key].append(interpolator(condition.airspeed))

        # Now interpolate: RPM -> thrust (at target airspeed)
        thrusts_at_target_airspeed = np.array(airspeed_interpolators[Columns.THRUST])

        # Filter out NaN values for the final interpolation
        valid_mask = ~np.isnan(thrusts_at_target_airspeed)
        if valid_mask.sum() < 2:
            if not self.silent:
                print(f"Not enough valid data points to interpolate for airspeed={condition.airspeed}")
            return None

        valid_rpms = self.prop.rpms[valid_mask]
        valid_thrusts = thrusts_at_target_airspeed[valid_mask]

        # Check if target thrust is within achievable range
        if condition.thrust < valid_thrusts.min() or condition.thrust > valid_thrusts.max():
            if not self.silent:
                print(
                f"Target thrust {condition.thrust} is outside the achievable range "
                f"[{valid_thrusts.min():.2f}, {valid_thrusts.max():.2f}] "
                f"at airspeed {condition.airspeed}"
            )
            return None

        rpm_interpolator = interp1d(valid_thrusts, valid_rpms,
                                    kind='cubic', fill_value=np.nan)

        # Find RPM that gives the target thrust
        required_rpm = float(rpm_interpolator(condition.thrust))

        # Build the result dictionary
        result = {'rpm': required_rpm}
        result: dict[str | Columns, float]

        # Interpolate additional parameters at the required RPM
        for param_name, param_values in airspeed_interpolators.items():
            if len(param_values) > 0:  # If this parameter was provided
                param_array = np.array(param_values)
                valid_mask = ~np.isnan(param_array)
                valid_params = param_array[valid_mask]

                param_interpolator = interp1d(valid_thrusts, valid_params,
                                              kind='cubic', fill_value=np.nan)
                result[param_name] = float(param_interpolator(condition.thrust))

        return result