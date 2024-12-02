# Training

In `scripts/`, there are scripts setup for training. Depending on the system (i.e., cluster, locally, etc.), you may need to run different commands.

## Local

To run locally, you can use the `local.sh` script. For example, you can run:

```bash
bash scripts/local.sh scripts/train.sh exp=<EXPERIMENT>
```

```{tip}
The `local.sh` script will automatically set `MUJOCO_GL=egl`. Training should always
be done with `MUJOCO_GL=egl` cause that runs with a headless implementation of OpenGL
and is significantly faster.
```

```{note}
You can also run `eval.sh` to run evaluation to visualize the env.
Set the `render_modes` to include `'human'` to visualize the env. It will also
automatically save the video to `logs/<date>/<exp>/eval.*`. Use `-h` to see options.
```

## Running on a cluster

We have provided scripts to run on three clusters: [SuperCloud](https://supercloud.mit.edu), [OpenMind](https://mcgovern.mit.edu/tile/openmind-computing-cluster/), and [Euler](https://euler-cluster.readthedocs.io/en/latest/). Coupled with these scripts are the [Slurm-based launcher configuration](https://hydra.cc/docs/plugins/submitit_launcher/), located at `configs/hydra/launcher/`. When running on a cluster, a daemon job will always be launched to monitor the training process; this is a requirement of hydra and will simply block until the training is complete.

To run, you can use the `supercloud.sh`, `openmind.sh`, or `euler.sh` scripts. For example, you can run:

```bash
# Note the `sbatch` command is used to submit the job to the cluster using Slurm.
sbatch scripts/supercloud.sh scripts/train.sh exp=<EXPERIMENT>
```

```{todo}
We plan to add AWS support in the future.
```

## Running evolution

In the above examples, we are simply running a single training loop. If you want to run an evolutionary experiment, you can use the `evo.sh` script. For example, you can run:

```bash
bash scripts/local.sh scripts/evo.sh exp=<EXPERIMENT>
```

`local.sh` can be replaced with `supercloud.sh`, `openmind.sh`, or `euler.sh` depending on the cluster you are using (remember to use `sbatch` in this case). The evolution loop utilizes the [`nevergrad` sweeper](https://hydra.cc/docs/plugins/nevergrad_sweeper/), and it's configs are located at `configs/hydra/sweeper/`.

In total, you should see `min(hydra.sweeper.optim.num_workers, hydra.launcher.array_parallelism) + 1` jobs. The `+ 1` is for the daemon job that monitors the training process. See the [`evolution_nevergrad.yaml`](https://github.com/camera-culture/ACI/blob/main/configs/hydra/sweeper/evolution_nevergrad.yaml) and [`slurm.yaml`](https://github.com/camera-culture/ACI/blob/main/configs/hydra/launcher/slurm.yaml) for more info.

### Resuming a failed evolution

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

## Running a training sweep

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

```{warning}
By default, sweeps will write to the same `logs` directory since they all share
the same experiment name. Ensure you set `expname` to a value which utilizes a sweep
parameter to differentiate between runs, e.g.
`expname=<EXPNAME>_\${param1}_\${param2}`.

Alternatively, you can add `+overlays=sweep` to the command to automatically add the
sweep parameters to the experiment name.
```

```{note}
The basic sweeper will sweep through _all_ permutations of the parameters. This can
be very slow for large sweeps. For more advanced sweeps, consider using optimization
via `scripts/evo.sh` ([see above](#running-evolution)).
```
