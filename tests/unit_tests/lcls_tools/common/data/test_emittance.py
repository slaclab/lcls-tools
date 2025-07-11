from unittest import TestCase
import numpy as np
from lcls_tools.common.data.emittance import compute_emit_bmag


class EmittanceCalculationTest(TestCase):
    def test_emittance_calc(self):
        # set up test values
        beamsize_squared = np.array(
            [
                [[0.00299705], [0.12034662], [0.03792509]],
                [[0.00259244], [0.23703413], [0.09598636]],
            ]
        )

        rmat = np.array(
            [
                [
                    [[-0.24254679, 1.04600053], [-1.17140665, 0.92885986]],
                    [[-1.16646303, 0.71788384], [-0.8039517, -0.36251133]],
                    [[-0.55801204, -0.55330746], [0.61964408, -1.17765613]],
                ],
                [
                    [[-0.24254679, 1.04600053], [-1.17140665, 0.92885986]],
                    [[-1.16646303, 0.71788384], [-0.8039517, -0.36251133]],
                    [[-0.55801204, -0.55330746], [0.61964408, -1.17765613]],
                ],
            ]
        )

        twiss_design = np.array(
            [
                [
                    [0.29970473, -1.58494282],
                    [12.03466156, -9.17146332],
                    [3.79250871, 3.01307483],
                ],
                [
                    [0.1296221, -0.66578778],
                    [11.85170667, -9.88871364],
                    [4.79931781, 2.87869131],
                ],
            ]
        )

        # compute emittance & bmag
        result = compute_emit_bmag(
            beamsize_squared=beamsize_squared, rmat=rmat, twiss_design=twiss_design
        )

        # compare results with ground-truth
        assert np.allclose(result["emittance"], np.array([[0.01], [0.02]]), rtol=1e-2)
        assert np.allclose(
            result["bmag"], np.array([[1.0, 1.0, 1.0], [1.0, 1.0, 1.0]]), rtol=1e-2
        )

    def test_emittance_calc_with_broadcast_twiss(self):
        # set up test values
        beamsize_squared = np.array(
            [
                [[0.00299705], [0.12034662], [0.03792509]],
                [[0.00259244], [0.23703413], [0.09598636]],
            ]
        )

        rmat = np.array(
            [
                [
                    [[-0.24254679, 1.04600053], [-1.17140665, 0.92885986]],
                    [[-1.16646303, 0.71788384], [-0.8039517, -0.36251133]],
                    [[-0.55801204, -0.55330746], [0.61964408, -1.17765613]],
                ],
                [
                    [[-0.24254679, 1.04600053], [-1.17140665, 0.92885986]],
                    [[-1.16646303, 0.71788384], [-0.8039517, -0.36251133]],
                    [[-0.55801204, -0.55330746], [0.61964408, -1.17765613]],
                ],
            ]
        )

        twiss_design = np.array(
            [
                [[0.29970473, -1.58494282]],
                [[0.1296221, -0.66578778]],
            ]
        )

        # compute emittance & bmag
        result = compute_emit_bmag(
            beamsize_squared=beamsize_squared, rmat=rmat, twiss_design=twiss_design
        )

        # compare results with ground-truth
        assert np.allclose(result["emittance"], np.array([[0.01], [0.02]]), rtol=1e-2)
        assert np.allclose(
            result["bmag"],
            np.array(
                [[1.0, 57.03675912, 27.39475026], [1.0, 59.93946213, 28.76180068]]
            ),
            rtol=1e-2,
        )
