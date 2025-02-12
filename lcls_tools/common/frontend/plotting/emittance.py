import matplotlib.pyplot as plt
import numpy as np
from lcls_tools.common.measurements.emittance_measurement import EmittanceMeasurementResult


def plot_quad_scan_result(emittance_results: EmittanceMeasurementResult):
    """
    Plot the results of a quad scan emittance measurement.
    """
    fig, ax = plt.subplots(2, 1)
    fig.set_size_inches(4, 9)

    ax[0].plot(emittance_results.quadrupole_strengths, emittance_results.x_rms,"+",label="x_rms")
    ax[0].plot(emittance_results.quadrupole_strengths, emittance_results.y_rms,"+",label="y_rms")

    # plot fit from twiss at screen calculation
    ax[0].plot(emittance_results.quadrupole_strengths, np.sqrt(emittance_results.twiss_fit["beta_x"]*emittance_results.twiss_fit["emittance_x"]),"--",label="x_fit")
    ax[0].plot(emittance_results.quadrupole_strengths, np.sqrt(emittance_results.twiss_fit["beta_y"]*emittance_results.twiss_fit["emittance_y"]),"--",label="y_fit")

    ax[0].set_xlabel("Quadrupole Strength [T/m]")
    ax[0].set_ylabel("Emittance [m]")

    ax[1].plot(emittance_results.quadrupole_strengths, emittance_results.BMAG)
    ax[1].set_xlabel("Quadrupole Strength [T/m]")
    ax[1].set_ylabel("BMAG")

    for ele in ax:
        ele.legend()

    return fig, ax              