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

    c = ["x", "y"]
    for i in range(2):
        sorted_indices = np.argsort(emittance_results.quadrupole_pv_values[i])
        k = emittance_results.quadrupole_pv_values[i][sorted_indices]
        beta = emittance_results.twiss_at_screen[i][sorted_indices][:, 0]

        ax[0].plot(
            k,
            emittance_results.rms_beamsizes[i][sorted_indices] * 1e6,
            "+",
            label=f"rms_{c[i]}",
        )

        # plot fit from twiss at screen calculation
        ax[0].plot(
            k,
            np.sqrt(beta * emittance_results.emittance[i]) * 1e3,
            "--",
            label=f"{c[i]}_fit",
        )

        if emittance_results.bmag is not None:
            ax[1].plot(
                k, emittance_results.bmag[i][sorted_indices], "+", label=f"bmag {c[i]}"
            )
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

    ax[0].set_xlabel("Quadrupole Strength [T/m]")
    ax[0].set_ylabel("Beam size [um]")

    for ele in ax:
        ele.legend()

    fig.tight_layout()
    return fig, ax
