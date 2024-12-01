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
bash scripts/supercloud.sh scripts/train.sh exp=<EXPERIMENT>
```

```{todo}
We plan to add AWS support in the future.
```

## Running Evolution

In the above examples, we are simply running a single training loop. If you want to run an evolutionary experiment, you can use the `evo.sh` script. For example, you can run:

```bash
bash scripts/local.sh scripts/evo.sh exp=<EXPERIMENT>
```

`local.sh` can be replaced with `supercloud.sh`, `openmind.sh`, or `euler.sh` depending on the cluster you are using. The evolution loop utilizes the [`nevergrad` sweeper](https://hydra.cc/docs/plugins/nevergrad_sweeper/), and it's configs are located at `configs/hydra/sweeper/`.

In total, you should see `min(hydra.sweeper.optim.num_workers, hydra.launcher.array_parallelism) + 1` jobs. The `+ 1` is for the daemon job that monitors the training process. See the [`evolution_nevergrad.yaml`](https://github.com/camera-culture/ACI/blob/main/configs/hydra/sweeper/evolution_nevergrad.yaml) and [`slurm.yaml`](https://github.com/camera-culture/ACI/blob/main/configs/hydra/launcher/slurm.yaml) for more info.
