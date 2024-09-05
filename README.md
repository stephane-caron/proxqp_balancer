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

### HPIPM

HPIPM is not packaged, but instructions to install from source are given in [hpipm](https://github.com/giaf/hpipm#python):

- Clone BLASFEO: `git clone https://github.com/giaf/blasfeo.git`
- From the BLASFEO directory, run: `make shared_library -j 4`
- Check again that you are in your conda environment, then run:

```console
cp -f ./lib/libblasfeo.so ${CONDA_PREFIX}/lib/
cp -f ./include/*.h ${CONDA_PREFIX}/include/
```

- Clone HPIPM: `git clone https://github.com/giaf/hpipm.git`
- From the HPIPM directory, run: `make shared_library -j 4`
- Check again that you are in your conda environment, then run:

```console
cp -f libhpipm.so ${CONDA_PREFIX}/lib/
cp -f ./include/*.h ${CONDA_PREFIX}/include/
```

- Go to `hpipm/interfaces/python/hpipm_python` and run `pip install .`
- Try to import the package in Python:

```py
import hpipm_python.common as hpipm
```

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
