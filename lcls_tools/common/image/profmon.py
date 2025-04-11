import lcls_tools.common.data.least_squares
import numpy

curve_dict = {
    "gaussian": lcls_tools.common.data.least_squares.gaussian,
    "asymmetrical_gaussian": lcls_tools.common.data.least_squares.asymmetrical_gaussian,
    "super_gaussian": lcls_tools.common.data.least_squares.super_gaussian,
    "asymmetrical_super_gaussian": lcls_tools.common.data.least_squares.asymmetrical_super_gaussian,
}


def profile_stat(profile, curve="gaussian"):
    fit = curve_dict[curve]
    params = fit(profile)
    stat = {"centroid": params["mu"], "rms_size": params["sigma"]}
    return stat


def image_stat(image, curve="gaussian"):
    x_projection = numpy.array(numpy.sum(image, axis=0))
    y_projection = numpy.array(numpy.sum(image, axis=1))
    x_stat = profile_stat(x_projection, curve=curve)
    y_stat = profile_stat(y_projection, curve=curve)
    centroid = [x_stat["centroid"], y_stat["centroid"]]
    rms_size = [x_stat["rms_size"], y_stat["rms_size"]]
    stat = {
        "centroid": centroid,
        "rms_size": rms_size,
        "intensity": image.sum(),
    }
    return stat
