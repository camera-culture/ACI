# Hydra

Hydra is a Python package designed to simplify the configuration management of complex applications. It enables users to compose, override, and manage configurations dynamically, making it especially useful for applications that need to handle multiple runtime scenarios, such as machine learning experiments or distributed systems.

## Features

Hydra provides a range of features to streamline configuration management:

- **Dynamic Composition**: Combine multiple configuration files or objects to define application behavior.
- **Overrides**: Modify configurations directly from the command line or programmatically.
- **Structured Configs**: Support for hierarchical and type-safe configurations using dataclasses or YAML.
- **Plugins**: Extend Hydra’s functionality with a rich ecosystem of plugins, including support for launching jobs on various platforms.
- **Experiment Tracking**: Log and organize experiment configurations automatically.

## Usage

We use Hydra to manage configurations for our experiments. The configuration files are stored in the `configs/` directory and each configuration file is composed of other configuration files via the `defaults` field. See [Config Composition](./config.md) for more information on how to use Hydra in this project.
