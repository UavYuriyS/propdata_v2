## Propeller data parser

This command-line software is used to find propellers in the APC [database](https://www.apcprop.com/technical-information/performance-data/) 
by name or search a most suitable propeller given multiple flight conditions and constraints


## Installation
* Clone this repo

    `git clone https://github.com/UavYuriyS/propdata_v2`
* Install the project requirements

    `pip install -r requirements.txt`

* Run the software

    `python propdata_v2.py --prop 9x8 --aspd 20 --thrust 6`


## Modes of operation
There are two main operation modes
* Manual one-point search
* Propeller optimisation

### One propeller and one flight condition
* Evaluates propeller parameters one prop and one flight condition. 
* It is required to provide `--prop`, `--aspd`, `--thrust` arguments for this mode to work
* The output for 9x8 prop and evaluation conditions of 20m/s and 6N should look like this
```
Fetched and interpolated data for prop 9x8, source: https://www.apcprop.com/files/PER3_9x8.dat
Prop dimensions: 9.0x8.0
Required RPM: 8758
Advance Ratio: 0.5993
Thrust Coefficient (Ct): 0.0841
Power Coefficient (Cp): 0.0702
Prop efficiency: 0.7213
Motor power: 166.9218
Motor torque: 0.1817
```

### Propeller optimisation
* Selecting the most efficient propeller subject to a number of constraints and a number of flight conditions
* This requires a `--constraints` argument with a path to a yaml config file
* Currently, only the `power`, `torque`, `rpm`, `dia` constraints are supported, with both low and high values

Example yaml config file
```yaml
# Constraint section
constraints:
  - name: absolute_maximum_parameters
    entries:
      - name: power
        low: 0
        high: 320
      - name: torque
        low: 0
        high: 0.197
      # Omitting the low/high value means that no check is performed
      - name: rpm
        high: 13000
  
  # You can group constraints together, like it is done here for physical and geometrical constraints
  - name: diameter_limit
    entries:
      - name: dia
        low: 6
        high: 12

conditions:
  # There might be more than one flight condition to evaluate the prop for
  - name: takeoff
    airspeed: 3
    thrust: 12
    
  # Weight is a relative value signifying the importance of a certain flight condition
  # By default a weight of 1 is assigned
  - name: cruise
    airspeed: 25
    thrust: 6.12
    weight: 20
```

The output might look like this
```
Evaluated 448 props, 26 matches, 5 best power efficiencies
Conditions: ConditionEntry(name='takeoff', thrust=12, airspeed=3, weight=1.0) ConditionEntry(name='cruise', thrust=6.12, airspeed=25, weight=20) ConditionEntry(name='low_speed_pass', thrust=1.67, airspeed=8, weight=3)
Prop: 875x825nn, 
	dimensions: 8.75x8.25, 
	efficiency: 0.1420 0.7556 0.6016 
	RPM: 12276.6343 10404.2506 4854.2797 
	torque: 0.1970 0.1862 0.0437 
	power: 253.5476 202.5334 22.2145
Prop: 875x75n, 
	dimensions: 8.75x7.5, 
	efficiency: 0.1534 0.7538 0.6095 
	RPM: 11625.8945 10601.6431 4799.0853 
	torque: 0.1925 0.1830 0.0434 
	power: 234.6876 203.1839 21.9536
Prop: 875x775nn, 
	dimensions: 8.75x7.75, 
	efficiency: 0.1468 0.7538 0.6024 
	RPM: 12318.0310 10743.7332 4954.9738 
	torque: 0.1903 0.1806 0.0423 
	power: 245.1370 203.0757 22.1777
Prop: 875x75nn, 
	dimensions: 8.75x7.5, 
	efficiency: 0.1486 0.7524 0.6021 
	RPM: 12310.0265 10864.0514 4986.8137 
	torque: 0.1881 0.1789 0.0429 
	power: 242.3175 203.3958 22.1864
Prop: 875x80nn, 
	dimensions: 8.75x8.0, 
	efficiency: 0.1480 0.7512 0.6023 
	RPM: 12297.2356 10776.9040 4947.8641 
	torque: 0.1889 0.1801 0.0430 
	power: 243.1784 203.7660 22.1896


The best propeller (values at condition ConditionEntry(name='cruise', thrust=6.12, airspeed=25, weight=20))):
Fetched and interpolated data for prop 875x825nn, source: https://www.apcprop.com/files/PER3_875x825NN.dat
Prop dimensions: 8.75x8.25
Required RPM: 10404
Advance Ratio: 0.6487
Thrust Coefficient (Ct): 0.0681
Power Coefficient (Cp): 0.0584
Prop efficiency: 0.7556
Motor power: 202.5334
Motor torque: 0.1862
```


## Propeller data caching
* By default, the propeller data is cached at `~/.propdata/data.pkl` and reused on the subsequent calls to this program
* If you want to force-download a new copy, you can remove that file or provide a `--force_download` flag to the command

P.s. I completely looked over the fact that you can grab a zip file with all the performance data
instead of parsing the website with xpath and what not. Submit a PR to fix this if you wish because I'm too lazy to do it