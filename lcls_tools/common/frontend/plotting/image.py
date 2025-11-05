import importlib
import numpy as np
from matplotlib import pyplot as plt

from lcls_tools.common.image.fit import ImageProjectionFitResult


def plot_image_projection_fit(result: ImageProjectionFitResult):
    """
    plot image and projection data for validation
    """
    fig, ax = plt.subplots(3, 1)
    fig.set_size_inches(4, 9)

    image = result.image
    c = ax[0].imshow(image)
    fig.colorbar(c, ax=ax[0])

    projections = {
        "x": np.array(np.sum(image, axis=0)),
        "y": np.array(np.sum(image, axis=1)),
    }
    centroid = np.array(
        (
            result.projection_fit_parameters[0]["mean"],
            result.projection_fit_parameters[1]["mean"],
        )
    )

    ax[0].plot(*centroid, "+r")

    module = importlib.import_module(
        f"lcls_tools.common.model.{result.projection_fit_module}"
    )

    # plot data and model fit
    for i, name in enumerate(["x", "y"]):
        fit_params = result.projection_fit_parameters[i]
        ax[i + 1].text(
            0.01,
            0.99,
            "\n".join([f"{name}: {val:.2f}" for name, val in fit_params.items()]),
            transform=ax[i + 1].transAxes,
            ha="left",
            va="top",
            fontsize=10,
        )
        x = np.arange(len(projections[name]))

        ax[i + 1].plot(projections[name], label="data")
        fit_params.pop("error")
        ax[i + 1].plot(
            module.curve(x, **fit_params), label="model fit"
        )

    return fig, ax
