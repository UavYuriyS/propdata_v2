#  "THE BEER-WARE LICENSE" (Revision 42):
#
#  <y.sukhorukov.uav@gmail.com> wrote this file.
#  As long as you retain this notice you can do whatever you want with this stuff.
#  If we meet some day, and you think this stuff is worth it, you can buy me a beer in return.
#  Yuriy Sukhorukov

from __future__ import annotations

import argparse
import warnings
from pathlib import Path
from typing import Optional, get_args
from typing import get_type_hints
from urllib.parse import urljoin

from tqdm import tqdm

from config import ConstraintEntry, ConstraintConfig, ConditionEntry
from data_loader import DataLoader
from interpolator import PropInterpolator
from models import Prop, Columns

warnings.filterwarnings('ignore')


parser = argparse.ArgumentParser(
    prog='PropDataV2',
    description=f'This grabs the data from the APC website and caches it. \n'
                f'If a prop name is provided, it evaluates the propeller parameters at a given airspeed and thrust \n'
                f'If no prop name is given, finds the most efficient prop for given flight conditions \n'
                f'Constraint file format: for now, only those constraint values are supported: '
                f'{get_args(get_type_hints(ConstraintEntry)["name"])}',
    epilog='Remember: this data is a result of a simulation. \n'
           'Use with caution.'
)

group = parser.add_mutually_exclusive_group(required=True)
parser.add_argument("--file", help="path to parsed data", default="~/.propdata/data.pkl")
group.add_argument('--prop', help="prop name", default=None)
parser.add_argument('--aspd', help="airspeed to evaluate prop efficiencies", type=float, default=None)
parser.add_argument('--thrust', help="thrust to evaluate prop efficiencies", type=float, default=None)
parser.add_argument('--force_download', help="force download new prop data", action="store_true", default=False)
group.add_argument('--constraints', help='path to a constraint file', default=None)


args = parser.parse_args()

constraints: Optional[ConstraintConfig] = None
if args.constraints:
    constraints = ConstraintConfig.load_config(args.constraints)

data_file = Path(args.file).expanduser().resolve()
data = DataLoader(data_file, args.force_download).load()

candidates = []

# Evaluate prop data for a given prop (this bypasses config and all that cool stuff)
if args.prop is not None:

    if args.aspd is None or args.thrust is None:
        print("Both airspeed and thrust should be provided. Terminating")
        exit(-1)

    for prop in data:
        # Exact match
        if args.prop == prop.name:
            candidates = [prop]
            break
        if prop.name.startswith(args.prop):
            candidates.append(prop)

    if len(candidates) == 0:
        print(f"No matches found, "
              f"check {urljoin(DataLoader.MAIN_API, DataLoader.PERF_DATA)} "
              f"for available props")
        exit(-1)

    if len(candidates) == 1:
        print(f"Fetching info for {candidates[0].name} prop")

    if len(candidates) > 1:
        print(f"Found the following matches: "
              f"{' '.join([p.name for p in candidates])} \n"
              f"Please refine your input")
        exit(-1)

    prop = candidates[0]

    interp = PropInterpolator(prop)
    result = interp.evaluate_point(
        ConditionEntry(
            name=prop.name,
            airspeed=args.aspd,
            thrust=args.thrust,
        )
    )

else:
# Find the best prop, evaluating multiple flight conditions
    print("Finding the optimal propeller", flush=True)

    # outer list - one entry per prop
    # inner list - for a prop, one entry for a flight condition
    # tuple - prop object and output from the interpolator (dict of value_name: value)
    results: list[list[tuple[Prop, dict[Columns | str, float]]]] = []
    for prop in tqdm(data):
        prop: Prop
        constraints_met = True
        res_for_condition = []
        interp = PropInterpolator(prop, silent=True)

        # Get the experiment results for this prop at all conditions
        for condition in constraints.conditions:
            prop_res = (prop, interp.evaluate_point(condition))

            # Some props can't provide a certain values for the given Condition
            # Set a flag to skip them
            if prop_res[1] is None:
                constraints_met = False
                # Terminate early
                break

            # Constrain those fields
            constraint_data = {
                'rpm': prop_res[1]['rpm'],
                'dia': prop_res[0].dia,
                'power': prop_res[1][Columns.POWER],
                'torque': prop_res[1][Columns.TORQUE]
            }

            # Set the flag to skip over all props that fail constraints
            if constraints and not constraints.does_match(constraint_data):
                constraints_met = False
                # Terminate early
                break
            res_for_condition.append(prop_res)

        # Skip over all props that fail constraints and can't provide thrust
        if constraints_met:
            results.append(res_for_condition)

    def weight_efficiencies(prop_results: list[tuple[Prop, dict[Columns | str, float]]]) -> float:
        return sum([
            prop_result[1][Columns.PROP_EFF]*cond.weight
            for prop_result, cond in zip(prop_results, constraints.conditions)
        ])

    # Calculate weighted efficiencies
    results_sorted = sorted(results, key=weight_efficiencies, reverse=True)

    print(f"\n\nEvaluated {len(data)} props, {len(results_sorted)} matches, 5 best power efficiencies")
    print(f"Conditions: {' '.join([str(cond) for cond in constraints.conditions])}")
    for experiment in results_sorted[:5]:
        print(f"Prop: {experiment[0][0].name}, \n\t"
              f"dimensions: {experiment[0][0].dia}x{experiment[0][0].pitch}, \n\t"
              f"efficiency: {' '.join(['{:.4f}'.format(res[1][Columns.PROP_EFF]) for res in experiment])} \n\t"
              f"RPM: {' '.join(['{:.4f}'.format(res[1]['rpm']) for res in experiment])} \n\t"
              f"torque: {' '.join(['{:.4f}'.format(res[1][Columns.TORQUE]) for res in experiment])} \n\t"
              f"power: {' '.join(['{:.4f}'.format(res[1][Columns.POWER]) for res in experiment])}")

    # Get the data for best prop
    best_prop = results_sorted[0]
    condition, (prop, result) = max(zip(constraints.conditions, best_prop), key=lambda x: x[0].weight)

    print(f'\n\nThe best propeller (values at condition {condition})):')

print(f"Fetched and interpolated data for prop {prop.name}, source: {prop.link}")
print(f"Prop dimensions: {prop.dia}x{prop.pitch}")
print(f"Required RPM: {result['rpm']:.0f}")
print(f"Advance Ratio: {result[Columns.ADV_RATIO]:.4f}")
print(f"Thrust Coefficient (Ct): {result[Columns.THRUST_COEFF]:.4f}")
print(f"Power Coefficient (Cp): {result[Columns.POWER_COEFF]:.4f}")
print(f"Prop efficiency: {result[Columns.PROP_EFF]:.4f}")
print(f"Motor power: {result[Columns.POWER]:.4f}")
print(f"Motor torque: {result[Columns.TORQUE]:.4f}")