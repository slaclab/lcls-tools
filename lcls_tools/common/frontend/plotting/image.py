import numpy as np
from matplotlib import pyplot as plt, patches


def plot_image_projection_fit(fit_object, results, n_stds=3):
    """
    plot image and projection data for validation
    """
    fig, ax = plt.subplots(3, 1)
    fig.set_size_inches(4, 9)

    image = results["processed_image"]
    ax[0].imshow(image)

    projections = {
        "x": np.array(np.sum(image, axis=0)),
        "y": np.array(np.sum(image, axis=1))
    }

    ax[0].plot(*results["centroid"], "+r")
    p0 = results["centroid"] - results["rms_sizes"] * n_stds
    rect = patches.Rectangle(
        p0, *results["rms_sizes"] * 2.0 * n_stds, facecolor="none", edgecolor="r"
    )
    ax[0].add_patch(rect)

    # plot data and model fit
    for i, name in enumerate(["x", "y"]):
        fit_params = results["projection_fit_parameters"][name]
        ax[i + 1].text(0.01, 0.99,
                       "\n".join([
                           f"{name}: {val: 4.2}" for name, val in fit_params.items()
                       ]),
                       transform=ax[i + 1].transAxes,
                       ha='left', va='top', fontsize=10)
        x = np.arange(len(projections[name]))

        ax[i + 1].plot(projections[name], label="data")
        fit_param_numpy = np.array([fit_params[name] for name in
                                    fit_object.projection_fit_method.parameters.parameters])
        ax[i + 1].plot(fit_object.projection_fit_method._forward(x, fit_param_numpy),
                       label="model fit")

    return fig, ax
