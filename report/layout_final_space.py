"""Candidate anchors for the figures of the final report (build_final.js): for each figure the element ids it may
follow (default first; ids from `DUMP=1 node build_final.js`) and the allowed width fractions."""
SPACE = {
    "fig1_motivation.png": ([11, 6, 8, 9, 10, 13, 15], [1.0, 0.9]),
    "fig2_pipeline.png": ([22, 13, 15, 18, 21, 24], [1.0]),
    "fig_architecture_final.png": ([28, 18, 21, 22, 24, 26, 30, 31, 32], [1.0]),
    "fig_method.png": ([36, 30, 31, 32, 33, 34, 35, 42, 44, 45, 48], [1.0, 0.9]),
    "fig_final_rates.png": ([91, 88, 89, 90, 93, 94], [1.0, 0.9]),
    "fig_nsysu_tide_a.png": ([104, 97, 100, 102, 103, 105], [1.0, 0.9]),
    "fig_nsysu_tide_b.png": ([104, 100, 102, 103, 105, 107], [1.0, 0.9]),
    "fig_bells.png": ([104, 102, 103, 105, 107, 108], [1.0, 0.9]),
    "fig_final_weeks.png": ([105, 104, 107, 108, 109], [1.0, 0.9]),
    "fig_ntu_moves.png": ([109, 105, 107, 108, 111, 114], [1.0, 0.9]),
    "fig_moves_check.png": ([109, 107, 108, 111, 114, 115], [1.0]),
    "fig_model.png": ([115, 111, 114, 116, 117], [1.0, 0.9]),
    "fig_horizon.png": ([116, 115, 117, 119], [1.0, 0.9]),
    "fig_nsysu.png": ([120, 117, 119, 121, 123], [1.0, 0.9]),
    "fig_final_transfer.png": ([121, 120, 123, 124, 125], [1.0, 0.9]),
    "fig_sim_ci.png": ([123, 121, 124, 125, 127], [1.0, 0.9]),
    "fig_final_forecast.png": ([131, 127, 130, 132, 134], [1.0, 0.9]),
    "fig_final_planner.png": ([135, 132, 134, 136], [1.0, 0.9]),
    "fig_demo_app.png": ([136, 134, 135, 138, 141, 142, 143], [1.0, 0.9, 0.8]),
}
