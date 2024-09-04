# MPC balancer

Model predictive controller used in the real-robot experiments of [PROXQP: an Efficient and Versatile Quadratic Programming Solver for Real-Time Robotics Applications and Beyond](https://inria.hal.science/hal-04198663v2).

## Installation

We recommend using Anaconda to install the agent and all dependencies in a clean environment:

```console
conda create -f environment.yaml
conda activate proxqp_balancer
```

Alternatively, you should be able to install the packages listed in the environment file from PyPI.

## Usage

To run in simulation, clone the [upkie](https://github.com/upkie/upkie) repository and run:

```console
./start_simulation.sh
```

Activate your conda environment and run the agent by:

```console
python proxqp_balancer.py
```
