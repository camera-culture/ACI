# Setup

This page provides setup and installation information for the `ACI` repo.

## Prerequisites

- Python >= 3.11

### Optional Prerequisites

- [Docker](https://docs.docker.com/get-docker/)

Clone the repo:

### Conda Environment

You may want to create a Python environment to isolate the dependencies for this
project. You can do this with `conda`. You will need to have `conda` installed.

```bash
conda create -n cambrian python=3.12
conda activate cambrian
```

## Installation

First, clone the repo:

```
git clone https://github.com/camera-culture/ACI.git
```

Then you can install the `cambrian` package by doing the following. You will first
need to install `poetry` if you don't already have it:

```
pip install poetry
poetry install
```

## TL;DR

Run the following to create a simple environment and save the run as a video.
The `--record` flag optionally takes an integer argument to specify the number of
timesteps to record. The resulting video will be saved to
`logs/<the date>/example/eval.*`.

```bash
python cambrian/envs/env.py run_renderer exp=example --record 100
```

> [!NOTE]
> The `example` experiment will use optics. On Mac, this is very slow since it uses
> pytorch when doing convolutions, so beware this may take upwards of 1 minute to run.
> Replace `example` with any other experiments in `configs/exp` to test other
> experiments

## Visualizing the world/environment

There is a runner in `env.py` that will visualize the world. You have a few run options:

```bash
# Interactive + Display
# Run with the custom visualization viewer in birds-eye view mode. This is interactive,
# so you can pan the renderer around using the mouse. You may need to set MUJOCO=glfw
# explicitly to have this work properly.
MUJOCO_GL=glfw python cambrian/envs/env.py run_renderer exp=<EXPERIMENT> env.renderer.render_modes="[human]"

# Noninteractive + headless
# Run the custom viewer but headless and save the output
# NOTE: This is non-interactive and should probably be run headless
python cambrian/envs/env.py run_renderer exp=<EXPERIMENT> --record <OPTIONAL_TOTAL_TIMESTEPS>

# Interactive + Display
# Run with built in mujoco viewer. You will need to scroll out to see the full view.
python cambrian/envs/env.py run_mj_viewer exp=<EXPERIMENT>
```

You can pass `-h` to see all options. Look in `configs/exp` for all the experiments
you can run. For more details on the mujoco viewer, [see below](#mujoco-viewer).

### Custom Viewer

This is a custom viewer that we use for debugging. There are a few shortcuts you can
use:

- `R`: Reset the environment
- `Tab`: Switch cameras in the main view
- `Space`: Pause the simulation
- `Exit`: Close the window

### Mujoco Viewer

Hover over an option on the left side and right click to show all the shortcuts. `Q` will visualize the cameras and their frustums. You can also just click it under **Rendering**.

## Running training

```bash
bash scripts/local.sh scripts/train.sh exp=<EXPERIMENT>
```

> [!TIP]
> The `local.sh` script will automatically set `MUJOCO_GL=egl`. Training should always
be done with `MUJOCO_GL=egl` cause that runs with a headless implementation of OpenGL
and is significantly faster.

> [!NOTE]
> You can also run `eval.sh` to run evaluation to visualize the env.
Set the `render_modes` to include `'human'` to visualize the env. It will also
automatically save the video to `logs/<date>/<exp>/eval.*`. Use `-h` to see options.

## Running evo

```bash
bash scripts/local.sh scripts/evo.sh exp=<EXPERIMENT>
```

> [!NOTE]
> You may get an error saying something along the lines
> `No variable to optimize in this parametrization.` This is because the config you
> chose doesn't have sweep parameters. You can either add some via the command line
> (see the [hydra documentation](https://hydra.cc/docs/intro)), add them to the
> config file or choose another exp.

## Running on Supercloud

To run on supercloud, replace `local.sh` with `supercloud.sh` in the above commands.
This will set various environment variables that are required to run on supercloud. You
can still run `local.sh` if you don't plan to use slurm to submit a job.

> [!NOTE]
> See `configs/hydra/launcher/supercloud.yaml` and
> `configs/hydra/sweeper/evolution.yaml` for the slurm and evolution settings,
> respectively.

### Training

```bash
# If running headless
sbatch scripts/supercloud.sh scripts/train.sh exp=<EXPERIMENT>
# If running in interactive mode
bash scripts/local.sh scripts/train.sh exp=<EXPERIMENT>
```

### Evaluation

```bash
# If running headless
sbatch scripts/supercloud.sh scripts/eval.sh exp=<EXPERIMENT>
# If running in interactive mode
bash scripts/local.sh scripts/eval.sh exp=<EXPERIMENT>
```

### Evo

```bash
# If running headless
sbatch scripts/supercloud.sh scripts/evo.sh exp=<EXPERIMENT>
# If running in interactive mode
bash scripts/local.sh scripts/evo.sh exp=<EXPERIMENT>
```

## Running on Openmind

To run on Openmind, the commands are exactly the same as running on supercloud, but
replace `supercloud.sh` with `openmind.sh`.

## Running a Training Sweep

By default, evolution uses nevergrad for optimization. But it may be useful to run a
simple grid search of different parameters. This can be done via Hydra's basic sweeper
functionality. To run a sweep, which trains each agent with a different set of
parameters, you can run the following:

```bash
# If running on a slurm-enabled cluster
sbatch scripts/<CLUSTER>.sh scripts/train.sh exp=<EXPERIMENT> <SWEEP_PARAMS> --multirun
# If running locally
bash scripts/local.sh scripts/train.sh exp=<EXPERIMENT> <SWEEP_PARAMS> --multirun
```

Running on a cluster can aid in parallelizing the training process. And note the
`--multirun` flag (can also `-m`) is required to run a sweep.

The simplest way to specify sweep params is via a comma separated list, e.g.
`... param1=1,2,3 param2='[1,2],[3,4]'`. The previous example will run six total runs,
iterating through all the permutations of the grid search. Please refer to
[Hydra's sweeper documentation](https://hydra.cc/docs/1.0/tutorials/basic/running_your_app/multi-run/#internaldocs-banner)
for more detailed information and specific override syntax support. To use
interpolations within the sweep, you must specify each interpolation prefixed with `\$`,
as in `expname=<EXPNAME>_\${param1}_\${param2}`.

> [!WARNING]
> By default, sweeps will write to the same `logs` directory since they all share
> the same experiment name. Ensure you set `expname` to a value which utilizes a sweep
> parameter to differentiate between runs, e.g.
> `expname=<EXPNAME>_\${param1}_\${param2}`.

> [!NOTE]
> The basic sweeper will sweep through _all_ permutations of the parameters. This can
> be very slow for large sweeps. For more advanced sweeps, consider using optimization
> via `scripts/evo.sh` ([see above](#running-evo)).

### Resuming a Failed Sweep

> [!NOTE]
> This is only implemented for the nevergrad sweeper.

To resume a failed sweep for the nevergrad sweeper, you simply need to rerun your
experiment. The nevergrad resuming logic is handled in hydra and enabled via the
`optim.load_if_exists` parameter in the config. This will load the optimizer state
from the last checkpoint and continue the optimization.

Keep in mind that the default path nevergrad will look for a optimizer pickle to load
is at `<logdir>/nevergrad.pkl`. If you're resuming an evolutionary run launched on a
different day, you may need to either:

1. Copy the failed evolutionary logdir to a new log directory matching the logdir
pattern for that day (recommended).
2. Change the logdir to the previous day
(i.e. `... logdir=logs/<old date>/${expname}`).
3. Change the optimizer path in the config to point to the correct path. This may cause
issues down the line with the `parse_evos.py` script since the output log directory is
in two places.

## Other things

### Introspection into the Configs

You can introspect into the configs by running the following:

```bash
python <ANY SCRIPT> exp=<EXPERIMENT> -c all
```

This will print out the entire config. You can print out specific parts of the config
using `-p <dot.separated.path>`.

```bash
python <ANY SCRIPT> exp=<EXPERIMENT> -p <dot.separated.path>
```

> [!NOTE]
> This is hydra syntax. For more information, run `python <ANY SCRIPT> --hydra-help`.

### Configs/Overrides

All configs should be put under `configs`. These are parsed by
[hydra](https://hydra.cc/docs/intro) and can be overridden by passing in
`<dot.separated.path>=<value>` to the script. Checkout hydra's documentation for more
details.
