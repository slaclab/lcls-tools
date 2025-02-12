import matplotlib.pyplot as plt
import numpy as np
from lcls_tools.common.measurements.emittance_measurement import EmittanceMeasurementResult


def plot_quad_scan_result(emittance_results: EmittanceMeasurementResult):
    """
    Plot the results of a quad scan emittance measurement.
    """
    fig, ax = plt.subplots(2, 1,sharex=True)
    fig.set_size_inches(4, 6)

    ax[0].plot(emittance_results.quadrupole_strengths, emittance_results.x_rms*1e6,"+",label="x_rms")
    ax[0].plot(emittance_results.quadrupole_strengths, emittance_results.y_rms*1e6,"+",label="y_rms")

    # plot fit from twiss at screen calculation
    ax[0].plot(
        emittance_results.quadrupole_strengths, 
        np.sqrt(emittance_results.twiss_at_screen[0,:,0]*emittance_results.emittance[0])*1e3,"--",label="x_fit")
    ax[0].plot(
        emittance_results.quadrupole_strengths, 
        np.sqrt(emittance_results.twiss_at_screen[1,:,0]*emittance_results.emittance[1])*1e3,"--",label="y_fit")

    # ax[0].set_xlabel("Quadrupole Strength [T/m]")
    ax[0].set_ylabel("Beam size [um]")


    ax[1].plot(emittance_results.quadrupole_strengths, emittance_results.BMAG[0], "+",label="BMAG x")
    ax[1].plot(emittance_results.quadrupole_strengths, emittance_results.BMAG[1], "+",label="BMAG y")

    ax[1].set_xlabel("Quadrupole Strength [T/m]")
    ax[1].set_ylabel("BMAG")
    ax[1].axhline(1.0, color="black", linestyle="--")

    for ele in ax:
        ele.legend()

    fig.tight_layout()
    return fig, ax              