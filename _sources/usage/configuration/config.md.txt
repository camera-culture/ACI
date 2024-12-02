# Configuration

This package uses [`hydra`](./hydra.md) extensively for configuration management. All config files are located within the [`configs/`](https://github.com/camera-culture/ACI/tree/main/configs) directory. Each config is defined by a schema which is used to validate the config.

## Config Schema

Each config schema is defined within the file which it's used; for instance, [`MjCambrianEnvConfig`](https://camera-culture.github.io/ACI/reference/api/cambrian/envs/index.html#cambrian.envs.MjCambrianEnvConfig) is defined in [`env.py`](https://github.com/camera-culture/ACI/blob/02fa04cd38c3b4d73c9ff4cc8e67ec08114507be/cambrian/envs/env.py#L62). The schema is implemented as a dataclass and added to the [Hydra ConfigStore](https://hydra.cc/docs/tutorials/structured_config/config_store/) using the [`config_wrapper` decorator](https://camera-culture.github.io/ACI/reference/api/cambrian/utils/config/index.html#cambrian.utils.config.config_wrapper). Thus, the associated config file should implement this schema; for instance, [`configs/env/env.yaml`](https://github.com/camera-culture/ACI/blob/main/configs/env/env.yaml) implements the `MjCambrianEnvConfig` schema.

## Config Composition

To reduce redundancy, configs are composed using the [Default List](https://hydra.cc/docs/advanced/defaults_list/) in hydra. For instance, [`MjCambrianMazeEnvConfig`](https://camera-culture.github.io/ACI/reference/api/cambrian/envs/index.html#cambrian.envs.MjCambrianMazeEnvConfig) (which inherits from `MjCambrianEnvConfig`) is defined in [`configs/env/maze_env.yaml`](https://github.com/camera-culture/ACI/blob/main/configs/env/maze_env.yaml) and simply includes the default `env` like the following:

```yaml
defaults:
  # This inherits from the default env config
  - env

  # Tells hydra to use the MjCambrianMazeEnvConfig schema
  - /MjCambrianMazeEnvConfig

# Anything remaining in this file overrides or adds to the default env config
# ...
```

This same logic applies in many other scenarios throughout the config definitions.

## Other things

### Config Introspection

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

### Configs Overrides

All configs should be put under `configs`. These are parsed by
[hydra](https://hydra.cc/docs/intro) and can be overridden by passing in
`<dot.separated.path>=<value>` to the script. Checkout hydra's documentation for more
details.
