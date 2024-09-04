# MPC balancer

Model predictive controller used in the real-robot experiments of [PROXQP: an Efficient and Versatile Quadratic Programming Solver for Real-Time Robotics Applications and Beyond](https://inria.hal.science/hal-04198663v2).

This is an archival repository: the code here matches the one used in the experiments of the paper. Check out the [MPC balancer](https://github.com/upkie/mpc_balancer) for future developments, bug fixes and support.

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

## Citation

If you use ProxQP or code from this repository in your works, please cite it as follows:

```bibtex
@unpublished{bambade2023proxqp,
    title = {{PROXQP: an Efficient and Versatile Quadratic Programming Solver for Real-Time Robotics Applications and Beyond}},
    author = {Bambade, Antoine and Schramm, Fabian and Kazdadi, Sarah El and Caron, St{\'e}phane and Taylor, Adrien and Carpentier, Justin},
    url = {https://inria.hal.science/hal-04198663},
    note = {working paper or preprint},
    year = {2023},
    month = Sep,
}
```

## See also

- [MPC balancer](https://github.com/upkie/mpc_balancer): where future development on this code will happen.
