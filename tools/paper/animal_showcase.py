from pathlib import Path
from typing import Dict, List, Optional

import mujoco as mj

from cambrian.renderer import MjCambrianRendererSaveMode
from cambrian.utils.config import (
    MjCambrianBaseConfig,
    MjCambrianConfig,
    config_wrapper,
    run_hydra,
)
from cambrian.utils.logger import get_logger


@config_wrapper
class AnimalShowcaseConfig(MjCambrianBaseConfig):
    """The configuration for the agent showcase.

    Attributes:
        logdir (Path): The primary directory which simulation data is stored in. This is
            the highest level directory used for saving the showcase outdir.
        outdir (Path): The directory used for saving the showcase. This is the directory
            where the showcase's data is stored. Should evaluate to
            `logdir` / `outsubdir`.
        outsubdir (Path): The subdirectory relative to `logdir` where the showcase's
            data is stored. This is the directory where the showcase's data is
            actually stored.

        exp (str): The experiment to run. This is the path to the hydra exp file
            as if you are you running the experiment from the root of the project
            (i.e. relative to the exp/ directory).

        mask (Optional[List[str]]): The masks to apply to overrides dict. If a mask is
            provided, only the overrides that match the mask will be used. If None,
            all overrides will be used.
        ignore (Optional[List[str]]): The overrides to ignore. If an override is in
            this list, it will not be used.

        steps (int): The number of steps to run the experiment for.

        overrides (Dict[str, List[str]]): The overrides to apply to the loaded
            configuration. This is a number of overrides that are used to generate
            images. The image is saved using the key as the filename and the value as
            the overrides to apply to the configuration.
    """

    logdir: Path
    outdir: Path
    outsubdir: Path

    exp: str

    mask: Optional[List[str]] = None
    ignore: Optional[List[str]] = None

    steps: int

    overrides: Dict[str, List[str]]


def main(config: AnimalShowcaseConfig, *, overrides: List[str]):
    if config.mask is not None:
        for m in config.mask:
            assert m in config.overrides, f"Mask {m} not in overrides"

    overrides = [*overrides, f"exp={config.exp}", "hydra/sweeper=basic"]
    for fname, exp_overrides in config.overrides.items():
        if config.ignore is not None and fname in config.ignore:
            continue
        if config.mask is not None and fname not in config.mask:
            continue

        get_logger().info(f"Composing agent showcase {fname}...")
        exp_config = MjCambrianConfig.compose(
            Path.cwd() / "configs",
            "base",
            overrides=[*exp_overrides, *overrides],
        )

        # Run the experiment
        # Involves first creating the environment and then rendering it
        get_logger().info(f"Running {config.exp}...")
        env = exp_config.env.instance(exp_config.env)

        env.record = True
        env.reset(seed=exp_config.seed)
        for agent in env.agents.values():
            agent.step()
        for _ in range(config.steps):
            mj.mj_step(env.model, env.data)
            env.render()
        config.outdir.mkdir(parents=True, exist_ok=True)
        env.save(
            config.outdir / fname,
            save_pkl=False,
            save_mode=MjCambrianRendererSaveMode.PNG,
        )

        # Save config and xml for debugging
        exp_config.save(config.outdir / f"{fname}.yaml")
        env.xml.write(config.outdir / f"{fname}.xml")


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser()

    parser.add_argument(
        "-o",
        "--override",
        "--overrides",
        dest="overrides",
        action="append",
        type=str,
        help="Global override config values. Do <config>.<key>=<value>. "
        "Used for all exps.",
        default=[],
    )

    run_hydra(
        main,
        config_path=Path.cwd() / "configs" / "tools" / "paper",
        config_name="agent_showcase",
        parser=parser,
    )
