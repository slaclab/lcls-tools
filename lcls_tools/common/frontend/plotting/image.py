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
    ax[0].imshow(image)

    projections = {
        "x": np.array(np.sum(image, axis=0)),
        "y": np.array(np.sum(image, axis=1)),
    }
    centroid = np.array(
        (
            result.x_projection_fit_parameters["mean"],
            result.y_projection_fit_parameters["mean"],
        )
    )

    ax[0].plot(*centroid, "+r")

    # plot data and model fit
    for i, name in enumerate(["x", "y"]):
        fit_params = getattr(result, f"{name}_projection_fit_parameters")
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
        fit_param_numpy = np.array(
            [
                fit_params[name]
                for name in result.projection_fit_method.parameters.parameters
            ]
        )
        ax[i + 1].plot(
            result.projection_fit_method._forward(x, fit_param_numpy), label="model fit"
        )

    return fig, ax
