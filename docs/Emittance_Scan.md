#Emittance Scan

##About 
The emittance scan is a tool that calculates and analyzes the emittance of an elecron beam. The Emittance is charaterized as the momentum of the electrons in the beam. A useful emittance is one that is as small as possible in a transverse demension.

##Emittance Scan Analysis Package
This [utility](https://github.com/slaclab/lcls-tools/blob/python3devel/lcls_tools/emit_scan/mat_emit_scan.py) can take an emittance scan .mat file and turn it into a python data object. The goal is to present the data from an emittance scan in a meaningful way. This utility has a [test file](https://github.com/slaclab/lcls-tools/blob/python3devel/lcls_tools/emit_scan/mat_emit_scan_test.py)  that is used for testing, but we can use it as an example. The full test is at the link above. 

Example: 'test_scan.mat'

Import and Initialize emit scan data object
```
>>> from mat_emit_scan import MatEmitScan as MES
>>> mes = MES('test_scan.mat')
```

Look at some metadata provided
```
>>> mes.fields
('status', 'type', 'name', 'quadName', 'quadVal', 'use', 'ts', 'beam', 'beamStd', 'beamList', 'chargeList', 'charge', 'chargeStd', 'rMatrix', 'twiss0', 'energy', 'twiss', 'twissstd', 'orbit', 'orbitstd', 'twissPV')
>>> mes.mat_file
'test_scan.mat'
>>> mes.status
[1, 1, 1, 1, 1, 1, 1, 1, 1, 1]
>>> mes.scan_type
'scan'
>>> mes.name
'YAGS:GUNB:753'
>>> mes.quad_name
'SOLN:GUNB:212'
>>> mes.quad_vals
array([ 0.072     ,  0.07288889,  0.07377778,  0.07466667,  0.07555556,
        0.07644444,  0.07733333,  0.07822222,  0.07911111,  0.08      ])
>>> mes.energy
0.00080999999999999996
>>> mes.emit_x
{'RMS': 3.4515596891751565, 'RMS floor': 9.7058411460479448, 'Asymmetric': 2.3011730612686216, 'RMS cut peak': 4.1500304671227708, 'Gaussian': 2.2849066179125792, 'RMS cut area': 2.4536073194623635, 'Super': 1.688336458977292}
>>> mes.beta_x
{'RMS': 80.484605665606026, 'RMS floor': 100.91535950661032, 'Asymmetric': 97.804316246866463, 'RMS cut peak': 76.108952766218465, 'Gaussian': 96.099462789374726, 'RMS cut area': 99.545334166075449, 'Super': 93.171709901593815}
>>> mes.alpha_x
{'RMS': -55.395171987314683, 'RMS floor': -69.88573148701731, 'Asymmetric': -67.660687952024801, 'RMS cut peak': -52.608008222157309, 'Gaussian': -66.480550801923854, 'RMS cut area': -68.518659896328131, 'Super': -64.492473842048952}
>>> mes.bmag_x
{'RMS': 1007.7399628928547, 'RMS floor': 1268.6334422248324, 'Asymmetric': 1228.6852675287346, 'RMS cut peak': 955.62547016282565, 'Gaussian': 1207.2601105065046, 'RMS cut area': 1246.4364849169979, 'Super': 1170.9257736052093}
```
There are more properties, but it's tough to list them all here.  Read the code to see all avialable properties until documentation is being written.  Hoping someone can sphinx this stuff.

Now for the beam property.  This is a bit disconcerting as in a cor plot scan, the beam property contains samples, but here it only seems to have one available sample (no list nesting).  Anyway, in this case it seems to be mes.beam[iteration][fit], where fit is the same FIT = ['Gaussian', 'Asymmetric', 'Super', 'RMS', 'RMS cut peak', 'RMS cut area', 'RMS floor'].  So in an example, say I want the 'profx' data for the 'Super' fit (index 2) for iteration 2 (index 1).
```
>>> mes.beam[1][2]['profx']
array([[-6737.52      , -6721.44      , -6705.36      , ...,
         2942.64      ,  2958.72      ,  2974.8       ],
       [  164.        ,    15.        ,    77.        , ...,
          -52.        ,   163.        ,    84.        ],
       [   19.07582407,    19.07582407,    19.07582407, ...,
           19.07582407,    19.07582407,    19.07582407]])
```

We could find out that this beam structure is actually similar to how it is in the cor plot .mat scan.  Then we could use the same unpacking function here in emittance scan (or define a general factory method).  I leave that up to further validation, and maybe we can have a summer student work on that.


Example: 'test_scan.mat'

Import and Initialize emit scan data object
```
>>> from mat_emit_scan import MatEmitScan as MES
>>> mes = MES('test_scan.mat')
```

Look at some metadata provided
```
>>> mes.fields
('status', 'type', 'name', 'quadName', 'quadVal', 'use', 'ts', 'beam', 'beamStd', 'beamList', 'chargeList', 'charge', 'chargeStd', 'rMatrix', 'twiss0', 'energy', 'twiss', 'twissstd', 'orbit', 'orbitstd', 'twissPV')
>>> mes.mat_file
'test_scan.mat'
>>> mes.status
[1, 1, 1, 1, 1, 1, 1, 1, 1, 1]
>>> mes.scan_type
'scan'
>>> mes.name
'YAGS:GUNB:753'
>>> mes.quad_name
'SOLN:GUNB:212'
>>> mes.quad_vals
array([ 0.072     ,  0.07288889,  0.07377778,  0.07466667,  0.07555556,
        0.07644444,  0.07733333,  0.07822222,  0.07911111,  0.08      ])
>>> mes.energy
0.00080999999999999996
>>> mes.emit_x
{'RMS': 3.4515596891751565, 'RMS floor': 9.7058411460479448, 'Asymmetric': 2.3011730612686216, 'RMS cut peak': 4.1500304671227708, 'Gaussian': 2.2849066179125792, 'RMS cut area': 2.4536073194623635, 'Super': 1.688336458977292}
>>> mes.beta_x
{'RMS': 80.484605665606026, 'RMS floor': 100.91535950661032, 'Asymmetric': 97.804316246866463, 'RMS cut peak': 76.108952766218465, 'Gaussian': 96.099462789374726, 'RMS cut area': 99.545334166075449, 'Super': 93.171709901593815}
>>> mes.alpha_x
{'RMS': -55.395171987314683, 'RMS floor': -69.88573148701731, 'Asymmetric': -67.660687952024801, 'RMS cut peak': -52.608008222157309, 'Gaussian': -66.480550801923854, 'RMS cut area': -68.518659896328131, 'Super': -64.492473842048952}
>>> mes.bmag_x
{'RMS': 1007.7399628928547, 'RMS floor': 1268.6334422248324, 'Asymmetric': 1228.6852675287346, 'RMS cut peak': 955.62547016282565, 'Gaussian': 1207.2601105065046, 'RMS cut area': 1246.4364849169979, 'Super': 1170.9257736052093}
```
There are more properties, but it's tough to list them all here.  Read the code to see all avialable properties until documentation is being written.  Hoping someone can sphinx this stuff.

Now for the beam property.  This is a bit disconcerting as in a cor plot scan, the beam property contains samples, but here it only seems to have one available sample (no list nesting).  Anyway, in this case it seems to be mes.beam[iteration][fit], where fit is the same FIT = ['Gaussian', 'Asymmetric', 'Super', 'RMS', 'RMS cut peak', 'RMS cut area', 'RMS floor'].  So in an example, say I want the 'profx' data for the 'Super' fit (index 2) for iteration 2 (index 1).
```
>>> mes.beam[1][2]['profx']
array([[-6737.52      , -6721.44      , -6705.36      , ...,
         2942.64      ,  2958.72      ,  2974.8       ],
       [  164.        ,    15.        ,    77.        , ...,
          -52.        ,   163.        ,    84.        ],
       [   19.07582407,    19.07582407,    19.07582407, ...,
           19.07582407,    19.07582407,    19.07582407]])
```
##Note
We could find out that this beam structure is actually similar to how it is in the cor plot .mat scan.  Then we could use the same unpacking function here in emittance scan (or define a general factory method).  I leave that up to further validation.


