# Beam Calculations
-------------------
The Solenoid is a lense inside the LCLS that is used to correct the 
momentum of the individual electrons that compose the electron beam. 
This is crucial to maintaining the size and shape of the beam. 

-------------------------------
## Solenoid Calculation Package
The goal of this utility is to collect data from the electron beam 
as it passes through the solenoid and use that data to calculate the 
best position of the solenoid for what is needed. This package, 
found [here](https://github.com/slaclab/lcls-tools/tree/python3devel/lcls_tools/beam_calcs/sol_calc), 
is currently under development. 


Import and Initialize Solenoid calc. data object 
```
>>> from sol_calc import SolCalc as S
>>> s = S(0.05, 0.5, 0.1)
```

## Function uses: 
```
>>> s.x_vals
[]
>>> s.y_vals
[]
>>> s.x_stds
[]
>>> s.y_stds
[]
>>> s.b_vals
[]
>>> s.results
none
>>> s.gun_energy
e_gun, .5
>>> s.length
l, .05
>>> s.calc_p
momentum calculation
  gamma = 1.0 + (self._e_gun / 0.511)
  beta = sqrt(1.0 - (1/gamma)**2)
  return beta*gamma*sc.m_e*sc.c
>>> s.calc_K
Get the current K value
  return (b * sc.e) / (2*p)

```
The remaining functions are calculations that will be used to generate an x and y array.
The final function will then use the arrays to offset the previous solenoid calculation. 
This Utility is currently under development and any information into what these functions
actually do would be a helpful addition to this documentation.
----------------------------

## Solenoid Calculation Test
This utility will test the functions in the solenoid calculation package 
to ensure that the package will complete it's intended purpose. The full test can be found [here](https://github.com/slaclab/lcls-tools/blob/master/lcls_tools/beam_calcs/sol_calc/sol_calc_test.py)


More packages to come.