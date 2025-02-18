import matplotlib.pyplot as plt
import numpy as np


def plot_quad_scan_result(emittance_results):
    """
    Plot the results of a quad scan emittance measurement.

    Parameters
    ----------
    emittance_results : EmittanceMeasurementResult
        The results of a quad scan emittance measurement.

    Returns
    -------
    fig : matplotlib.figure.Figure
        The figure object.
    ax : numpy.ndarray
        The axis objects.
    """

    fig, ax = plt.subplots(2, 1, sharex=True)
    fig.set_size_inches(4, 6)

    sorted_indices = np.argsort(emittance_results.quadrupole_focusing_strengths)
    k = emittance_results.quadrupole_focusing_strengths[sorted_indices]
    beta = emittance_results.twiss_at_screen.transpose(1, 0, 2)[sorted_indices][..., 0]

    ax[0].plot(k, emittance_results.rms_x[sorted_indices] * 1e6, "+", label="x_rms")
    ax[0].plot(k, emittance_results.rms_y[sorted_indices] * 1e6, "+", label="y_rms")

    # plot fit from twiss at screen calculation
    ax[0].plot(
        k,
        np.sqrt(beta[:, 0] * emittance_results.emittance[0]) * 1e3,
        "--",
        label="x_fit",
    )
    ax[0].plot(
        k,
        np.sqrt(beta[:, 1] * emittance_results.emittance[1]) * 1e3,
        "--",
        label="y_fit",
    )

    # ax[0].set_xlabel("Quadrupole Strength [T/m]")
    ax[0].set_ylabel("Beam size [um]")

    if emittance_results.bmag is not None:
        ax[1].plot(k, emittance_results.bmag[0][sorted_indices], "+", label="bmag x")
        ax[1].plot(k, emittance_results.bmag[1][sorted_indices], "+", label="bmag y")

        ax[1].set_xlabel("Quadrupole Strength [T/m]")
        ax[1].set_ylabel("bmag")
        ax[1].axhline(1.0, color="black", linestyle="--")
    else:
        # add text to the middle of the axis that says "BMAG not available"
        ax[1].text(
            0.5,
            0.5,
            "bmag not available",
            ha="center",
            va="center",
            transform=ax[1].transAxes,
        )

    for ele in ax:
        ele.legend()

    fig.tight_layout()
    return fig, ax
