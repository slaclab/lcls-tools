=======
Data Analysis
=======

Data Analysis Classes
=================

These classes are used to hold data requested from the EPICS archiver.

.. autoclass:: lcls_tools.common.data_analysis.archiver.ArchiverValue
    :members:

.. autoclass:: lcls_tools.common.data_analysis.archiver.ArchiveDataHandler
    :members:

This class stores information for a given Process Variable (PV) so that it can be plotted with the PlottingBase class.

.. autoclass:: lcls_tools.common.data_analysis.archiver_data_process.PVModel
    :members:

This class is used to quickly visualize plots of PVs over time, or correlations between two PVs.

.. autoclass:: lcls_tools.common.data_analysis.plotting_base.PlottingBase
    :members:

Below are some examples that demonstrate basic functionality of PlottingBase. See above for more information on additional arguments for the plotting methods.

.. code-block:: python

    import plotting_base as pb
    import archiver_data_process as adp

    if __name__ == '__main__':
        # plot a PV over time
        toro_pv = adp.pv("TORO:GUNB:360:CHRG", "2024/07/01 00:00:00",
                         "2024/07/01 01:00:00")
        df_chrg = adp.create_df(toro_pv)
        plotter = pb.PlottingBase(pv_dataframes=[df_chrg])
        plotter.plot_pv_over_time()

        # changing start and end point and re-plotting
        toro_pv.start = "2024/06/30 23:00:00"
        toro_pv.end = "2024/07/01 00:00:00"
        df_chrg_new = adp.create_df(toro_pv)
        plotter_new = pb.PlottingBase(pv_dataframes=[df_chrg_new])
        plotter_new.plot_pv_over_time()

        # plot a correlation between two PVs
        hom_pv = adp.pv("SCOP:AMRF:RF01:AI_MEAS1", "2024/06/30 15:00:00",
                        "2024/07/01 01:00:00")
        df_hom = adp.create_df(hom_pv)
        df_correlation = (
            adp.merge_dfs_with_margin_by_timestamp_column(df_hom, df_chrg_new,
                                                          time_margin_seconds=0.1))
        plotter_correl = pb.PlottingBase(pv_dataframes=[df_hom, df_chrg_new],
                                         df_correlation=df_correlation,
                                         pv_x="TORO:GUNB:360:CHRG",
                                         pv_y="SCOP:AMRF:RF01:AI_MEAS1",
                                         is_scatter_plot=True,
                                         has_smart_title=True,
                                         has_smart_axis_labels=True,
                                         pv_y_label="HOM C1 Signal",
                                         pv_x_label="Charge",
                                         is_cmap=True,
                                         has_fit_line=True,
                                         figure_title_font_size=22)
        plotter_correl.plot_pvs_correlation()

Data Analysis Functions
=================

These functions access data from the EPICS archiver.

.. autofunction:: lcls_tools.common.data_analysis.archiver.get_data_at_time

.. autofunction:: lcls_tools.common.data_analysis.archiver.get_data_with_time_interval

.. autofunction:: lcls_tools.common.data_analysis.archiver.get_values_over_time_range

This function simply returns a PVModel for given parameters so that a PV can be plotted.

.. autofunction:: lcls_tools.common.data_analysis.archiver_data_process.pv

The following functions create DataFrames and merge them together by Timestamp for given PVs.

.. autofunction:: lcls_tools.common.data_analysis.archiver_data_process.create_df

.. autofunction:: lcls_tools.common.data_analysis.archiver_data_process.merge_dfs_by_timestamp_column

.. autofunction:: lcls_tools.common.data_analysis.archiver_data_process.merge_dfs_with_margin_by_timestamp_column