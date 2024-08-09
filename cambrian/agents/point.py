from typing import Dict, List, Any, Tuple, TYPE_CHECKING

import numpy as np
from gymnasium import spaces
import mujoco as mj

from cambrian.agents import MjCambrianAgent, MjCambrianAgentConfig

if TYPE_CHECKING:
    from cambrian.envs import MjCambrianEnv
    from cambrian.envs.maze_env import MjCambrianMazeEnv


class MjCambrianAgentPoint(MjCambrianAgent):
    """
    This is a hardcoded class which implements the agent as actuated by a forward
    velocity and a rotational position. In mujoco, to the best of my knowledge, all
    translational joints are actuated in reference to the _global_ frame rather than
    the local frame. This means a velocity actuator applied along the x-axis will move
    the agent along the global x-axis rather than the local x-axis. Therefore, the
    agent will have 3 actuators: two for x and y global velocities and one for
    rotational position. From the perspective the calling class (i.e. MjCambrianEnv),
    this agent has two actuators: a forward velocity and a rotational position. We will
    calculate the global velocities and rotational position from these two "actuators".

    TODO: Will create an issue on mujoco and see if it's possible to implement this
    in xml.
    """

    def _update_obs(self, obs: Dict[str, Any]) -> Dict[str, Any]:
        """Creates the entire obs dict."""
        obs = super()._update_obs(obs)

        # Update the action obs
        # Calculate the global velocities
        if self._config.use_action_obs:
            v, theta = self._calc_v_theta(self.last_action)
            theta = np.interp(theta, [-np.pi, np.pi], [-1, 1])
            obs["action"] = np.array([v, theta], dtype=np.float32)

        return obs

    def _calc_v_theta(self, action: Tuple[float, float, float]) -> Tuple[float, float]:
        """Calculates the v and theta from the action."""
        vx, vy, theta = action
        v = np.hypot(vx, vy)
        theta = np.arctan2(vy, vx) - self.qpos[2]
        return v, theta

    def apply_action(self, action: List[float]):
        """This differs from the base implementation as action only has two elements,
        but the model has three actuators. Calculate the global velocities here."""
        assert len(action) == 2, f"Action must have two elements, got {len(action)}."

        # map the v action to be between 0 and 1
        v = (action[0] + 1) / 2

        # Calculate the global velocities
        # NOTE: The third actuator is the hinge joint which defines the theta
        theta = self._data.qpos[self._actuators[2].trnadr]
        new_action = [v * np.cos(theta), v * np.sin(theta), action[1]]

        # Call the base implementation with the new action
        super().apply_action(new_action)

    @property
    def action_space(self) -> spaces.Space:
        """Overrides the base implementation to only have two elements."""
        return spaces.Box(low=-1, high=1, shape=(2,), dtype=np.float32)

    @MjCambrianAgent.quat.setter
    def quat(
        self, value: Tuple[float | None, float | None, float | None, float | None]
    ):
        """Overrides the base implementation to set the z rotation."""
        assert len(value) == 4, f"Quaternion must have 4 elements, got {len(value)}."
        # Only set quat if all values are not None
        if any(val is None for val in value):
            return

        self.qpos[self._qposadrs[2]] = np.arctan2(
            2 * (value[0] * value[3] + value[1] * value[2]),
            1 - 2 * (value[2] ** 2 + value[3] ** 2),
        )


class MjCambrianAgentPointPredator(MjCambrianAgentPoint):
    """This is an agent which is non-trainable and defines a custom policy which
    acts as a "predator" in the environment. This agent will attempt to catch the prey
    by taking actions that minimize the distance between itself and the prey.

    Keyword Arguments:
        preys (List[str]): The names of the preys in the environment. The prey states
            will be determined from this list by querying the env.
        speed (float): The speed of the predator. Default is 1.0. This is constant
            during the simulation. Must be between -1 and 1, where -1 is no movement.
    """

    def __init__(
        self,
        config: MjCambrianAgentConfig,
        name: str,
        idx: int,
        *,
        preys: List[str],
        speed: float = 1.0,
    ):
        super().__init__(config, name, idx)

        self._preys = preys
        self._speed = speed

    def get_action_privileged(self, env: "MjCambrianEnv") -> List[float]:
        """This is where the predator will calculate its action based on the prey
        states."""

        # Get the prey states
        prey_pos = [env.agents[prey].pos for prey in self._preys]

        # Calculate the distance between the predator and the closest prey
        distances = [np.linalg.norm(self.pos - pos) for pos in prey_pos]

        # Calculate the vector that minimizes the distance between the predator and the
        # closest prey
        min_distance_index = np.argmin(distances)
        min_distance_vector = prey_pos[min_distance_index] - self.pos

        # Calculate the delta from the current angle to the angle that minimizes the
        # distance
        min_distance_angle = np.arctan2(min_distance_vector[1], min_distance_vector[0])
        delta = min_distance_angle - self.last_action[-1]

        # Set the action based on the vector calculated above. Add some noise to the
        # angle to make the movement.
        def wrap_angle(angle):
            return (angle + np.pi) % (2 * np.pi) - np.pi

        return [self._speed, wrap_angle(delta + np.random.randn())]


class MjCambrianAgentPointPrey(MjCambrianAgentPoint):
    """This is an agent which is non-trainable and defines a custom policy which
    acts as a "prey" in the environment. This agent will attempt to avoid the predator
    by taking actions that maximize the distance between itself and the predator.

    Keyword Arguments:
        predators (List[str]): The names of the predators in the environment. The
            predator states will be determined from this list by querying the env.
        speed (float): The speed of the prey. Default is 1.0. This is constant during
            the simulation. Must be between -1 and 1, where -1 is no movement.
    """

    def __init__(
        self,
        config: MjCambrianAgentConfig,
        name: str,
        idx: int,
        *,
        predators: List[str],
        speed: float = 1.0,
    ):
        super().__init__(config, name, idx)

        self._predators = predators
        self._speed = speed

    def get_action_privileged(self, env: "MjCambrianEnv") -> List[float]:
        """This is where the prey will calculate its action based on the predator
        states."""

        # Get the predator states
        predator_pos = [env.agents[predator].pos for predator in self._predators]

        # Calculate the distance between the prey and the closest predator
        distances = [np.linalg.norm(self.pos - pos) for pos in predator_pos]

        # Calculate the vector that maximizes the distance between the prey and the
        # closest predator
        max_distance_index = np.argmax(distances)
        max_distance_vector = self.pos - predator_pos[max_distance_index]

        # Calculate the delta from the current angle to the angle that maximizes the
        # distance
        max_distance_angle = np.arctan2(max_distance_vector[1], max_distance_vector[0])
        delta = max_distance_angle - self.last_action[-1]

        # Set the action based on the vector calculated above. Add some noise to the
        # angle to make the movement.
        def wrap_angle(angle):
            return (angle + np.pi) % (2 * np.pi) - np.pi

        return [self._speed, wrap_angle(delta + np.random.randn())]


class MjCambrianAgentPointMazeOptimal(MjCambrianAgentPoint):
    """This is an agent which is non-trainable and defines a custom policy which
    acts as an optimal agent in the maze environment. This agent will attempt to reach
    the goal by taking actions that best map to the optimal trajectory which is
    calculated from the maze using bfs."""

    def __init__(
        self,
        config: MjCambrianAgentConfig,
        name: str,
        idx: int,
        *,
        target: str,
        speed: float = -0.75,
        distance_threshold: float = 2.0,
        use_optimal_trajectory: bool = True,
    ):
        super().__init__(config, name, idx)

        self._target = target
        self._speed = speed
        self._distance_threshold = distance_threshold

        self._optimal_trajectory: np.ndarray = None
        self._use_optimal_trajectory = use_optimal_trajectory

    def reset(self, model: mj.MjModel, data: mj.MjData) -> Dict[str, Any]:
        """Resets the optimal_trajectory."""
        self._optimal_trajectory = None
        return super().reset(model, data)

    def get_action_privileged(self, env: "MjCambrianMazeEnv") -> List[float]:
        if self._target in env.agents:
            agent_pos = env.agents[self._target].pos
            self._optimal_trajectory = np.array([agent_pos[:2]])
        else:
            raise ValueError(f"Target {self._target} not found in env")

        # Calculate the optimal trajectory if the current trajectory is None
        if self._optimal_trajectory is None:
            if self._use_optimal_trajectory:
                obstacles = []
                for agent_name, agent in env.agents.items():
                    if agent_name != self._target:
                        obstacles.append(tuple(env.maze.xy_to_rowcol(agent.pos)))
                self._optimal_trajectory = env.maze.compute_optimal_path(
                    self.pos, agent_pos, obstacles=obstacles
                )
            else:
                self._optimal_trajectory = np.array([agent_pos[:2]])

        # If the optimal_trajectory is empty, return no action. We've probably reached
        # the end
        if len(self._optimal_trajectory) == 0:
            self._optimal_trajectory = np.array([agent_pos[:2]])

        # Get the current target. If the distance between the current position and the
        # target is less than the threshold, then remove the target from the optimal
        # trajectory
        target = self._optimal_trajectory[0]
        target_vector = target - self.pos[:2]
        if np.linalg.norm(target_vector) < self._distance_threshold:
            self._optimal_trajectory = self._optimal_trajectory[1:]

        # Calculate the delta from the current angle to the angle that minimizes the
        # distance
        target_theta = np.arctan2(target_vector[1], target_vector[0])
        last_theta = self._calc_v_theta(self.last_action)[1]
        delta = target_theta - last_theta

        # Set the action based on the vector calculated above. Add some noise to the
        # angle to make the movement.
        delta = np.interp(delta, [-np.pi, np.pi], [-1, 1])
        return [self._speed, np.clip(delta, -1, 1)]