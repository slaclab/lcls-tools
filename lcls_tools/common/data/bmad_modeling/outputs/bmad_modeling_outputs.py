import matplotlib.pyplot as plt
import epics
from lcls_tools.common.data.bmad_modeling import bmad_modeling as mod


def plot_betas(output1, output2, **kwargs):
    """Generates two figures with beta.a and beta.b for two output runs"""
    plot_beta_options = {
        "title1": "",
        "title2": "",
        "label1": "Design",
        "label2": "Model",
        "figsize": (8, 4),
    }
    plot_beta_options.update(kwargs)
    opt = plot_beta_options
    fig1, ax1 = plt.subplots(figsize=(8, 4))
    ax1.plot(
        output1["ele.s"], output1["ele.a.beta"], label=opt["label1"], linestyle="--"
    )
    ax1.plot(output2["ele.s"], output2["ele.a.beta"], label=opt["label2"])
    plt.legend()
    # Add energy to the rhs
    ax12 = ax1.twinx()
    ax12.plot(output2["ele.s"], output2["ele.e_tot"] / 1e9, color="red")
    ax12.set_ylabel("Energy (GeV)")
    efinal = output2["ele.e_tot"][-1] / 1e9
    plt.title(f"{opt['title1']} Final energy: {efinal:.2f} GeV")
    ax1.set_xlabel("s (m)")
    ax1.set_ylabel("Twiss Beta X (m)")
    # itime = isotime()
    fig2, ax2 = plt.subplots(figsize=(8, 4))
    ax2.plot(
        output1["ele.s"], output1["ele.b.beta"], label=opt["label1"], linestyle="--"
    )
    ax2.plot(output2["ele.s"], output2["ele.b.beta"], label=opt["label2"])
    plt.legend()
    ax22 = ax2.twinx()
    ax22.plot(output2["ele.s"], output2["ele.e_tot"] / 1e9, color="red")
    ax22.set_ylabel("Energy (GeV)")
    plt.title(f"{opt['title2']} Final energy: {efinal:.2f} GeV")
    ax2.set_xlabel("s (m)")
    ax2.set_ylabel("Twiss Beta Y (m)")
    axes_list = [ax1, ax12, ax2, ax22]
    fig1.show()
    fig2.show()
    return fig1, fig2, axes_list


def disp_twiss(tao, element, datum=[]):
    """Display model beta_a, alpha_a, beta_b and alpha_b for given element as well as bmag with respect to desing."""
    """If datum is given, bmag with respect to model is calculated"""
    # parameters = ["beta_a", "alpha_a", "beta_b", "alpha_b"]
    if not datum == []:
        twiss_datum = tao.data_parameter(datum, "meas_value")[0]["data"][0:4]
        twiss_datum = [float(val) for val in twiss_datum]
        twiss_model = mod.get_twiss(tao, element, which="model")
        twiss_design = mod.get_twiss(tao, element)
        bmag_a, bmag_b = mod.bmag(twiss_model, twiss_design)
        print(f"\n{element} BMAG_X {bmag_a:3.2f}, BMAG_Y {bmag_b:3.2f} ")
        print(f"{' ' * 12} Beta     Alpha   Beta   Alpha ")
        print(f"{' ' * 12}  X       X       Y       Y")
        print(f"Desing:{' '} ", end="")
        for val in twiss_design:
            print(f"{val:8.2f}", end="")
        print("")
        print(f"Model:{' ' * 3}", end="")
        for val in twiss_model:
            print(f"{val:8.2f}", end="")
        print("")
        if not datum == []:
            print(f"Measured:{' ' * 0}", end="")
            for val in twiss_datum:
                print(f"{float(val):8.2f}", end="")
            bmag_a, bmag_b = mod.bmag(twiss_datum[0:4], twiss_model)
            print("\nMeasured to Model:")
            print(f"\n{element} BMAG_X {bmag_a:3.2f}, BMAG_Y {bmag_b:3.2f}")
        print("")


def quad_table(tao, pct_lim=1, show_energy=False):
    """Display table of quad elements BDES, BMOD, Bmad model
    BDES and  Bamd model energy.  Filter

    by pct_lim =  (BMOD - Bmad model)/ BMOD"""
    quads = tao.lat_list("quad::Q*", "ele.name", flags="-no_slaves")
    if show_energy:
        print("Ele.    Device            EACT    EDES    E_TOT    ")
    else:
        print("Ele.    Device           BDES    BMOD    Bmad     %")
    for element in quads[1:]:
        device = tao.ele_head(element)["alias"]
        bmod = epics.caget(device + ":BMOD")
        bdes = epics.caget(device + ":BDES")
        eact = epics.caget(device + ":EACT")
        edes = epics.caget(device + ":EDES")
        e_tot = tao.ele_gen_attribs(element)["E_TOT"] / 1e9

        model_bdes = mod.get_bmad_bdes(tao, element)
        if show_energy:
            print(f"{element:7s} {device:15s} {eact:7.3f}{edes:7.3f} {e_tot:7.3f}")
        else:
            percent = 100 * abs((bmod - model_bdes) / bmod) if bmod != 0 else 0
            if percent > pct_lim:
                print(
                    f"{element:7s} {device:15s} {bdes:7.3f}"
                    f"{bmod:7.3f} {model_bdes:7.3f} {percent:7.3}"
                )


def plot_twiss(tao, output, info="", xoff=0):
    """Plot twiss parameters for one output as well as element lables"""
    fig, ax = plt.subplots(figsize=(8, 4))
    ax.plot(output["ele.s"], output["ele.a.beta"], label=r"$\beta_a$")
    ax.plot(output["ele.s"], output["ele.b.beta"], label=r"$\beta_b$")
    plt.legend()
    # Add energy to the rhs
    ax2 = ax.twinx()
    ax2.plot(output["ele.s"], output["ele.e_tot"] / 1e9, color="red")
    ax2.set_ylabel("Energy (GeV)")
    ax.set_xlabel("s (m)")
    ax.set_ylabel("Twiss Beta (m)")
    efinal = output["ele.e_tot"][-1] / 1e9
    plt.title(f"{info} Final energy: {efinal:.2f} GeV")
    quads = tao.lat_list("quad::Q*", "ele.name", flags="-no_slaves")
    for q in quads:
        plt.text(
            tao.ele_head(q)["s"],
            -30,
            q,
            rotation=90,
            ha="center",
            va="center",
            fontsize=8,
            transform=ax.transData,
        )
    fig.show()
    return fig
