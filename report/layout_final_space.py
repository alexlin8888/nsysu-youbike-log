"""Candidate anchors for the figures of the final report (build_final.js): for each figure the element ids it may
follow (default first; ids from `DUMP=1 node build_final.js`) and the allowed width fractions."""
SPACE = {
    "fig1_motivation.png": ([11, 6, 8, 9, 10, 13, 15], [1.0, 0.9]),
    "fig2_pipeline.png": ([22, 13, 15, 18, 21, 24], [1.0]),
    "fig_architecture_final.png": ([28, 18, 21, 22, 24, 26, 30, 31, 32], [1.0]),
    "fig_method.png": ([36, 30, 31, 32, 33, 34, 35, 42, 44, 45, 48], [1.0, 0.9]),
    "fig_final_rates.png": ([91, 88, 89, 90, 93, 94, 95, 96, 97], [1.0, 0.9]),
    "fig_nsysu_tide_a.png": ([107, 100, 103, 105, 106, 108], [1.0, 0.9]),
    "fig_nsysu_tide_b.png": ([107, 103, 105, 106, 108, 110], [1.0, 0.9]),
    "fig_bells.png": ([107, 105, 106, 108, 110, 111], [1.0, 0.9]),
    "fig_final_weeks.png": ([108, 107, 110, 111, 112], [1.0, 0.9]),
    "fig_ntu_moves.png": ([112, 108, 110, 111, 114, 117], [1.0, 0.9]),
    "fig_moves_check.png": ([112, 110, 111, 114, 117, 118], [1.0]),
    "fig_model.png": ([118, 114, 117, 119, 120], [1.0, 0.9]),
    "fig_horizon.png": ([119, 118, 120, 122], [1.0, 0.9]),
    "fig_nsysu.png": ([123, 120, 122, 124, 126], [1.0, 0.9]),
    "fig_final_transfer.png": ([124, 123, 126, 127, 128], [1.0, 0.9]),
    "fig_sim_ci.png": ([126, 124, 127, 128, 130], [1.0, 0.9]),
    "fig_final_forecast.png": ([134, 130, 133, 135, 136], [1.0, 0.9]),
    "fig_final_time.png": ([140, 138, 139, 141, 142, 143], [1.0]),
    "fig_demo_app.png": ([146, 143, 144, 145, 148, 149], [1.0, 0.9, 0.8]),
    "fig_final_sim.png": ([149, 148, 150, 151, 152], [1.0, 0.9]),
}
