"""Candidate anchors for the figures of the final report (build_final.js): for each figure the element ids it may
follow (default first; ids from `DUMP=1 node build_final.js`) and the allowed width fractions."""
SPACE = {
    "fig1_motivation.png": ([11, 6, 8, 9, 10, 13, 15], [1.0, 0.9]),
    "fig2_pipeline.png": ([22, 13, 15, 18, 21, 24], [1.0]),
    "fig_architecture_final.png": ([28, 18, 21, 22, 24, 26, 30, 31, 32], [1.0]),
    "fig_method.png": ([36, 30, 31, 32, 33, 34, 35, 42, 44, 45, 48], [1.0, 0.9]),
    "fig_final_rates.png": ([91, 88, 89, 90, 93, 94, 95], [1.0, 0.9]),
    "fig_nsysu_tide_a.png": ([105, 98, 101, 103, 104, 106], [1.0, 0.9]),
    "fig_nsysu_tide_b.png": ([105, 101, 103, 104, 106, 108], [1.0, 0.9]),
    "fig_bells.png": ([105, 103, 104, 106, 108, 109], [1.0, 0.9]),
    "fig_final_weeks.png": ([106, 105, 108, 109, 110], [1.0, 0.9]),
    "fig_ntu_moves.png": ([110, 106, 108, 109, 112, 115], [1.0, 0.9]),
    "fig_moves_check.png": ([110, 108, 109, 112, 115, 116], [1.0]),
    "fig_model.png": ([116, 112, 115, 117, 118], [1.0, 0.9]),
    "fig_horizon.png": ([117, 116, 118, 120], [1.0, 0.9]),
    "fig_nsysu.png": ([121, 118, 120, 122, 124], [1.0, 0.9]),
    "fig_final_transfer.png": ([122, 121, 124, 125, 126], [1.0, 0.9]),
    "fig_sim_ci.png": ([124, 122, 125, 126, 128], [1.0, 0.9]),
    "fig_final_forecast.png": ([132, 128, 131, 133, 134], [1.0, 0.9]),
    "fig_final_rider.png": ([137, 134, 136, 138, 139, 140], [1.0]),
    "fig_demo_app.png": ([141, 138, 139, 140, 143, 144], [1.0, 0.9, 0.8]),
    "fig_final_sim.png": ([144, 143, 145, 146, 147], [1.0, 0.9]),
}
