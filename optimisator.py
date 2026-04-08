from tqdm import tqdm

from config import ConstraintConfig
from interpolator import PropInterpolator
from models import Prop, Columns


def optimize(constraints: ConstraintConfig, data: list[Prop]):
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

    return results