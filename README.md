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

Start the [pi3hat spine](https://upkie.github.io/upkie/spines.html#pi3hat-spine) to run the agent on your robot, or the [Bullet spine](https://upkie.github.io/upkie/spines.html#bullet-spine) to check the agent first in simulation (recommended). Then, run the agent by:

```console
python proxqp_balancer.py
```
