#  "THE BEER-WARE LICENSE" (Revision 42):
#
#  <y.sukhorukov.uav@gmail.com> wrote this file.
#  As long as you retain this notice you can do whatever you want with this stuff.
#  If we meet some day, and you think this stuff is worth it, you can buy me a beer in return.
#  Yuriy Sukhorukov

from dataclasses import dataclass
from typing import Optional, Literal

import numpy as np
from scipy.interpolate import interp1d

from config import ConditionEntry
from models import Columns, Prop

@dataclass
class PropInterpolator:
    prop: Prop
    silent: bool = False

    # Optionally add caching for interpolators but im lazy
    def evaluate_point(self, condition: ConditionEntry) -> Optional[dict[Columns | Literal["rpm"], float]]:
        airspeed_interpolated_params = {}
        airspeed_interpolated_params: dict[Columns | Literal["rpm"], list]

        # For each RPM, interpolate to find thrust and other params at the target airspeed
        for i, rpm in enumerate(self.prop.rpms):
            # Interpolate parameters
            for key, matrix in self.prop.matrices.items():
                if key not in airspeed_interpolated_params:
                    airspeed_interpolated_params[key] = []

                airspeeds = self.prop.matrices[Columns.AIRSPEED][i]
                _, unique_aspd_mask = np.unique(airspeeds, return_index=True)

                interpolator = interp1d(airspeeds[unique_aspd_mask], matrix[i][unique_aspd_mask], kind='cubic',
                                        bounds_error=False, fill_value=np.nan)
                airspeed_interpolated_params[key].append(interpolator(condition.airspeed))


        # Set up the interpolation sources and targets

        if (condition.input is not None) ^ (condition.input_value is not None):
            print("condition.input and condition.input_value should be either both set or unset")
            print("Defaulting to thrust as an input value")

        if condition.input is not None and condition.input_value is not None:
            interpolate_from = condition.input
            input_value = condition.input_value
        else:
            interpolate_from = Columns.THRUST
            input_value = condition.thrust
            if input_value is None:
                print("No input thrust provided, terminating now")
                exit(1)

        airspeed_interpolated_params['rpm'] = list(self.prop.rpms)

        # Now interpolate: RPM -> thrust (at target airspeed)
        interpolate_from_at_target_airspeed = np.array(airspeed_interpolated_params[interpolate_from])

        # Filter out NaN values for the final interpolation
        valid_mask = ~np.isnan(interpolate_from_at_target_airspeed)
        if valid_mask.sum() < 2:
            if not self.silent:
                print(f"Not enough valid data points to interpolate for airspeed={condition.airspeed}")
            return None

        valid_interpolate_from = interpolate_from_at_target_airspeed[valid_mask]
        airspeed_interpolated_params['rpm'] = list(self.prop.rpms[valid_mask])
        # Check if target thrust is within achievable range
        if not len(valid_interpolate_from) or input_value < valid_interpolate_from.min() or input_value > valid_interpolate_from.max():
            if not self.silent:
                print(
                f"Target {interpolate_from} {input_value} is outside the achievable range "
                f"[{valid_interpolate_from.min():.2f}, {valid_interpolate_from.max():.2f}] "
                f"at airspeed {condition.airspeed}"
            )
            return None

        # Build the result dictionary
        result: dict[Literal["rpm"] | Columns, float] = {}

        # Interpolate additional parameters at the required RPM
        for param_name, param_values in airspeed_interpolated_params.items():
            if len(param_values) > 0:  # If this parameter was provided
                param_array = np.array(param_values)
                valid_mask = ~np.isnan(param_array)
                valid_params = param_array[valid_mask]

                if interpolate_from == "rpm":
                    valid_interpolate_from = interpolate_from_at_target_airspeed[valid_mask]

                    if not len(valid_interpolate_from) or input_value < valid_interpolate_from.min() or input_value > valid_interpolate_from.max():
                        if not self.silent:
                            print(
                                f"Target rpm {input_value} is outside the achievable range "
                                f"at airspeed {condition.airspeed}"
                            )
                        return None

                param_interpolator = interp1d(valid_interpolate_from, valid_params,
                                              kind='cubic', fill_value=np.nan)
                result[param_name] = float(param_interpolator(input_value))

        return result