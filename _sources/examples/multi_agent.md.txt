# Implementing a Multi-Agent Task

This document describes how to train multi-agent systems using the ACI framework. This example is very similar to the [Detection](../detection/README.md) example, so you may want to read that first.

## Overview

Multi-agent training is not directly supported in ACI; [`stable-baselines3`](https://github.com/DLR-RM/stable-baselines3/issues/69) does not directly support multi-agent training in the sense that multiple policies cannot be trained in parallel. However, you can achieve a multi-agent-esque system by effectively tricking sb3 into thinking it's a single agent system. This is done by concatenating the observations and actions of all agents into a single observation and action space. This is a common technique in multi-agent training and is known as centralized training with decentralized execution. The downside of this approach is that there is still only one policy and value function, so the agents are not truly independent. If reward functions are adversarial, like if one agent is trying to maximize a reward while another is trying to minimize it, the resulting reward will always be zero and this approach won't work.

## Training

A multi-agent detection task has been provided and can be run using the following command:

```bash
bash scripts/local.sh scripts/train.sh exp=tasks/detection_ma
```

The config is provided below. The task itself is just the detection task, but with two agents rather than one.

```{literalinclude} ../../configs/exp/tasks/detection_ma.yaml
:language: yaml
```

## Example

```{video} assets/multi_agent.mp4
:loop:
:autoplay:
:muted:
:width: 100%
```
