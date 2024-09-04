#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# SPDX-License-Identifier: Apache-2.0
# Copyright 2023 Inria

"""Wheel balancing using model predictive control with the ProxQP solver."""

import abc
import argparse
import os
import time
from time import perf_counter
from typing import Optional

import gin
import gymnasium as gym
import numpy as np
import qpalm
import qpsolvers
import upkie.envs
from numpy.typing import NDArray
from proxsuite import proxqp
from qpmpc import MPCQP, Plan, solve_mpc
from qpmpc.systems import WheeledInvertedPendulum
from qpsolvers import solve_problem
from upkie.utils.clamp import clamp
from upkie.utils.filters import low_pass_filter
from upkie.utils.raspi import configure_agent_process, on_raspi
from upkie.utils.spdlog import logging

upkie.envs.register()

WHEEL_RADIUS = 0.06


def parse_command_line_arguments() -> argparse.Namespace:
    """
    Parse command line arguments.

    Returns:
        Command-line arguments.
    """
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--live-plot",
        help="Display a live plot of MPC trajectories",
        action="store_true",
        default=False,
    )
    parser.add_argument(
        "--solver",
        help="QP solver to use",
        choices=["proxqp", "qpalm"],
        default="proxqp",
    )
    return parser.parse_args()


class Workspace(abc.ABC):
    @abc.abstractmethod
    def solve(self, mpc_qp: MPCQP) -> qpsolvers.Solution:
        """Solve a new QP, using warm-starting if possible.

        Args:
            mpc_qp: New model-predictive control QP.

        Returns:
            Results from solver.
        """


@gin.configurable
class ProxQPWorkspace(Workspace):
    def __init__(
        self,
        mpc_qp: MPCQP,
        eps_abs: float,
        eps_rel: float,
        update_preconditioner: bool,
        verbose: bool,
    ):
        n_eq = 0
        n_in = mpc_qp.h.size // 2  # WheeledInvertedPendulum structure
        n = mpc_qp.P.shape[1]
        solver = proxqp.dense.QP(
            n,
            n_eq,
            n_in,
            dense_backend=proxqp.dense.DenseBackend.PrimalDualLDLT,
        )
        solver.settings.eps_abs = eps_abs
        solver.settings.eps_rel = eps_rel
        solver.settings.verbose = verbose
        solver.settings.compute_timings = True
        solver.settings.primal_infeasibility_solving = True
        solver.init(
            H=mpc_qp.P,
            g=mpc_qp.q,
            C=mpc_qp.G[::2, :],  # WheeledInvertedPendulum structure
            l=-mpc_qp.h[1::2],  # WheeledInvertedPendulum structure
            u=mpc_qp.h[::2],  # WheeledInvertedPendulum structure
        )
        solver.solve()
        self.update_preconditioner = update_preconditioner
        self.solver = solver

    def solve(self, mpc_qp: MPCQP) -> qpsolvers.Solution:
        self.solver.update(
            g=mpc_qp.q,
            update_preconditioner=self.update_preconditioner,
        )
        self.solver.solve()
        result = self.solver.results
        qpsol = qpsolvers.Solution(mpc_qp.problem)
        qpsol.found = result.info.status == proxqp.QPSolverOutput.PROXQP_SOLVED
        qpsol.x = self.solver.results.x
        return qpsol


@gin.configurable
class QPALMWorkspace(Workspace):

    def __init__(
        self, mpc_qp: MPCQP, eps_abs: float, eps_rel: float, verbose: bool
    ):
        settings = qpalm.Settings()
        settings.verbose = verbose
        settings.eps_abs = eps_abs
        settings.eps_rel = eps_rel

        P, q, G, h, A, b, lb, ub = mpc_qp.unpack()
        # P, G, A = ensure_sparse_matrices(P, G, A)
        n: int = q.shape[0]
        m: int = G.shape[0]
        data = qpalm.Data(n, m)
        data.Q = P
        data.q = q
        data.A = G
        data.bmax = h
        data.bmin = -h

        solver = qpalm.Solver(data, settings)
        solver.solve()
        self.solver = solver
        self.solution = None

    def solve(self, mpc_qp: MPCQP) -> qpsolvers.Solution:
        self.solver.update_q(mpc_qp.q)
        if self.solution is not None:
            self.solver.warm_start(self.solution.x, self.solution.y)
            self.solution = namedtuple("Solution", ["x", "y"])(x=None, y=None)
        self.solver.solve()
        self.solution.x = self.solver.solution.x
        self.solution.y = self.solver.solution.y
        qpsol = qpsolvers.Solution(mpc_qp.problem)
        qpsol.found = self.solver.info.status == "solved"
        qpsol.x = self.solver.solution.x
        return qpsol


@gin.configurable
def balance(
    env: gym.Env,
    max_ground_accel: float,
    mpc_sampling_period: float,
    nb_env_steps: int,
    nb_mpc_timesteps: int,
    pendulum_length: float,
    rebuild_qp_every_time: bool,
    show_live_plot: bool,
    stage_input_cost_weight: float,
    stage_state_cost_weight: float,
    terminal_cost_weight: float,
    warm_start: bool,
):
    """Run MPC balancer in gym environment with logging.

    Args:
        env: Gym environment to Upkie.
        nb_env_steps: Number of environment steps to perform (zero to run
            indefinitely).
        rebuild_qp_every_time: If set, rebuild all QP matrices at every
            iteration. Otherwise, only update vectors.
        show_live_plot: Show a live plot.
        stage_input_cost_weight: Weight for the stage input cost.
        stage_state_cost_weight: Weight for the stage state cost.
        terminal_cost_weight: Weight for the terminal cost.
        warm_start: If set, use the warm-starting feature of ProxQP.
    """
    pendulum = WheeledInvertedPendulum(
        length=pendulum_length,
        max_ground_accel=max_ground_accel,
        nb_timesteps=nb_mpc_timesteps,
        sampling_period=mpc_sampling_period,
    )
    mpc_problem = pendulum.build_mpc_problem(
        terminal_cost_weight=terminal_cost_weight,
        stage_state_cost_weight=stage_state_cost_weight,
        stage_input_cost_weight=stage_input_cost_weight,
    )
    mpc_problem.initial_state = np.zeros(4)
    mpc_qp = MPCQP(mpc_problem)
    workspace = ProxQPWorkspace(mpc_qp)

    live_plot = None
    if show_live_plot and not on_raspi():
        from qpmpc.live_plots import (  # imports matplotlib
            WheeledInvertedPendulumPlot,
        )

        live_plot = WheeledInvertedPendulumPlot(pendulum, order="velocities")

    env.reset()  # connects to the spine
    commanded_velocity = 0.0
    action = np.zeros(env.action_space.shape)

    planning_times = np.empty((nb_env_steps,)) if nb_env_steps > 0 else None
    base_pitches = np.empty((nb_env_steps,)) if nb_env_steps > 0 else None
    step = 0
    while True:
        action[0] = commanded_velocity
        observation, _, terminated, truncated, info = env.step(action)
        env.log("observation", observation)
        if terminated or truncated:
            observation, info = env.reset()
            commanded_velocity = 0.0

        spine_observation = info["spine_observation"]
        floor_contact = spine_observation["floor_contact"]["contact"]

        # Unpack observation into initial MPC state
        (
            base_pitch,
            ground_position,
            base_angular_velocity,
            ground_velocity,
        ) = observation
        initial_state = np.array(
            [
                ground_position,
                base_pitch,
                ground_velocity,
                base_angular_velocity,
            ]
        )

        nx = WheeledInvertedPendulum.STATE_DIM
        target_states = np.zeros((pendulum.nb_timesteps + 1) * nx)
        mpc_problem.update_initial_state(initial_state)
        mpc_problem.update_goal_state(target_states[-nx:])
        mpc_problem.update_target_states(target_states[:-nx])

        t0 = perf_counter()
        if rebuild_qp_every_time:
            plan = solve_mpc(mpc_problem, solver="proxqp")
        else:
            mpc_qp.update_cost_vector(mpc_problem)
            if warm_start:
                qpsol = workspace.solve(mpc_qp)
            else:
                qpsol = solve_problem(mpc_qp.problem, solver="proxqp")
            if not qpsol.found:
                logging.warn("No solution found to the MPC problem")
            plan = Plan(mpc_problem, qpsol)
        if nb_env_steps > 0:
            base_pitches[step] = base_pitch
            planning_times[step] = perf_counter() - t0

        if not floor_contact:
            commanded_velocity = low_pass_filter(
                prev_output=commanded_velocity,
                cutoff_period=0.1,
                new_input=0.0,
                dt=env.unwrapped.dt,
            )
        elif plan.is_empty:
            logging.error("Solver found no solution to the MPC problem")
            logging.info("Continuing with previous action")
        else:  # plan was found
            pendulum.state = initial_state
            if live_plot is not None:
                t = time.time()
                live_plot.update(plan, t, initial_state, t)
            commanded_accel = plan.first_input
            commanded_velocity = clamp_and_warn(
                commanded_velocity + commanded_accel * env.unwrapped.dt / 2.0,
                lower=-1.0,
                upper=+1.0,
                label="commanded_velocity",
            )

        if nb_env_steps > 0:
            step += 1
            if step >= nb_env_steps:
                break

    report(mpc_problem, mpc_qp, planning_times)
    np.save("base_pitches.npy", base_pitches)
    np.save("planning_times.npy", planning_times)


def report(mpc_problem, mpc_qp, planning_times: Optional[NDArray[float]]):
    average_ms = 1e3 * np.average(planning_times)
    std_ms = 1e3 * np.std(planning_times)
    nb_env_steps = planning_times.size
    print("")
    print(f"{gin.operative_config_str()}")
    print(f"{mpc_problem.goal_state=}")
    print(f"{mpc_problem.nb_timesteps=}")
    print(f"{mpc_qp.P.shape=}")
    print(f"{mpc_qp.q.shape=}")
    print(f"{mpc_qp.G.shape=}")
    print(f"{mpc_qp.h.shape=}")
    print(f"{mpc_qp.Phi.shape=}")
    print(f"{mpc_qp.Psi.shape=}")
    print("")
    if planning_times is not None:
        print(
            "Planning time: "
            f"{average_ms:.2} ± {std_ms:.2} ms over {nb_env_steps} calls"
        )
        print("")


if __name__ == "__main__":
    if on_raspi():
        configure_agent_process()

    agent_dir = os.path.dirname(__file__)
    gin.parse_config_file(f"{agent_dir}/config.gin")
    args = parse_command_line_arguments()
    with gym.make(
        "UpkieGroundVelocity-v3",
        frequency=200.0,
        wheel_radius=WHEEL_RADIUS,
        spine_config={
            "wheel_odometry": {
                "signed_radius": {
                    "left_wheel": -WHEEL_RADIUS,
                    "right_wheel": +WHEEL_RADIUS,
                }
            }
        },
    ) as env:
        balance(env, show_live_plot=args.live_plot)
