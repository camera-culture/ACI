from typing import Dict, Any, Optional, Self, Type
from dataclasses import field, dataclass, fields, make_dataclass
from pathlib import Path
from functools import partial

import hydra_zen as zen
from hydra.core.config_store import ConfigStore
from omegaconf import OmegaConf, DictConfig, ListConfig, MissingMandatoryValue

# =============================================================================
# Config classes and methods


class MjCambrianContainerConfig:
    """This is a wrapper around the OmegaConf DictConfig and ListConfig classes.

    Internally, hydra use OmegaConf to parse yaml/config files. OmegaConf
    uses an internal class DictConfig (and ListConfig for lists) to represent the
    dictionary data types. This is immutable and inheritance isn't easy, so this class
    allows us to wrap the DictConfig and ListConfig classes to add some additional
    methods. OmegaConf uses functional-style programming, where the OmegaConf class
    provides methods with which you pass a DictConfig or ListConfig instance to.
    Instead, we wrap the DictConfig and ListConfig classes to provide object-oriented
    programming, where we can call methods on the instance itself, as well as
    additional custom methods.

    We'll keep around two instances of DictConfig or ListConfig: `_config` and
    `_content`. `_config` is the original, uninstantiated config. This is strictly yaml
    and does not include any instantiated objects. `_content` is the instantiated
    config. When getting an attribute, we'll get the attribute from `_content` and
    return the wrapped instance by this class. `_config` is used to export in a human-
    readable format to a yaml file.

    Args:
        content (DictConfig | ListConfig): The instantiated config.

    Keyword Args:
        config (Optional[DictConfig | ListConfig]): The original, uninstantiated
            config. If unset, will use the content as the config.
    """

    _config: DictConfig | ListConfig
    _content: DictConfig | ListConfig

    def __init__(
        self,
        content: DictConfig | ListConfig,
        /,
        config: Optional[DictConfig | ListConfig] = None,
    ):
        # Must use __dict__ to set the attributes since we're overriding the
        # __getattr__ method. If config is None, we'll just set it to the content.
        self.__dict__["_content"] = content
        self.__dict__["_config"] = config or content

    @classmethod
    def instantiate(
        cls,
        config: DictConfig | ListConfig,
        **kwargs,
    ) -> DictConfig | ListConfig:
        """Instantiate the config using the structured config. Will check for missing
        keys and raise an error if any are missing."""
        # First instantiate the config (will replace _target_ with the actual class)
        # And then merge the structured config with the instantiated config to give it
        # validation.
        content = zen.instantiate(config, **kwargs)

        # Check for missing values. Error message will only show the first missing key.
        if keys := OmegaConf.missing_keys(content):
            content._format_and_raise(
                key=next(iter(keys)),
                value=None,
                cause=MissingMandatoryValue("Missing mandatory value"),
            )
        return MjCambrianContainerConfig(content, config=config)

    @classmethod
    def load(cls, **kwargs) -> Self:
        """Wrapper around OmegaConf.load to instantiate the config."""
        return cls.instantiate(OmegaConf.load(**kwargs))

    @classmethod
    def create(cls, **kwargs) -> Self:
        """Wrapper around OmegaConf.create to instantiate the config."""
        return cls.instantiate(OmegaConf.create(**kwargs))

    def get_type(self) -> Type[Any]:
        """Wrapper around OmegaConf.get_type to get the type of the config."""
        return OmegaConf.get_type(self._content)

    def to_container(self) -> Dict[str, Any]:
        """Wrapper around OmegaConf.to_container to convert the config to a
        dictionary."""
        return OmegaConf.to_container(self._config)

    def to_yaml(self) -> str:
        """Wrapper around OmegaConf.to_yaml to convert the config to a yaml string."""
        import yaml

        def str_representer(dumper: yaml.Dumper, data):
            """Will use the | style for multiline strings."""
            style = "|" if "\n" in data else None
            return dumper.represent_scalar("tag:yaml.org,2002:str", data, style=style)

        dumper = yaml.CSafeDumper
        dumper.add_representer(str, str_representer)
        return yaml.dump(
            self.to_container(),
            default_flow_style=False,
            allow_unicode=True,
            sort_keys=False,
            Dumper=yaml.CSafeDumper,
        )

    def save(self, path: Path | str):
        """Wrapper around OmegaConf.save to save the config to a yaml file."""
        return OmegaConf.save(self._config, path)

    def __getattr__(self, name: str) -> Self | Any:
        """Get the attribute from the content and return the wrapped instance. If the
        attribute is a DictConfig or ListConfig, we'll wrap it in this class."""
        content = self._content.__getattr__(name)
        if OmegaConf.is_config(content):
            config = self._config.__getattr__(name)
            return MjCambrianContainerConfig(content, config=config)
        else:
            return content

    def __str__(self) -> str:
        return self.to_yaml()


class MjCambrianDictConfig(MjCambrianContainerConfig, DictConfig):
    """This is a wrapper around the OmegaConf DictConfig class.

    It is intended that this class never actually be instantiated. Config classes
    should inherit from this class (or a base config class should inherit from this)
    such that when duck typing, all the methods of DictConfig and
    MjCambrianContainerConfig are available.
    """

    pass


def config_wrapper(cls=None, /, **kwargs):
    """This is a wrapper of the dataclass decorator that adds the class to the hydra
    store.

    The hydra store is used to construct structured configs from the yaml files.

    We'll also do some preprocessing of the dataclass fields such that all type hints
    are supported by hydra. Hydra only supports a certain subset of types, so we'll
    convert the types to supported types using the _sanitized_type method from
    hydra_zen.

    Keyword Args:
        kw: The kwargs to pass to the dataclass decorator. The following defaults
            are set:
            - repr: False
            - eq: False
            - slots: True
            - kw_only: True
    """

    # Update the kwargs for the dataclass with some defaults
    default_dataclass_kw = dict(repr=False, eq=False, slots=True, kw_only=True)
    kwargs = {**default_dataclass_kw, **kwargs}

    def wrapper(cls):
        # Preprocess the fields to convert the types to supported types
        # Only certain primitives are supported by hydra/OmegaConf, so we'll convert
        # these types to supported types using the _sanitized_type method from hydra_zen
        new_fields = []
        for f in fields(dataclass(cls, **kwargs)):
            new_fields.append((f.name, zen.DefaultBuilds._sanitized_type(f.type), f))

        # Create the new dataclass with the sanitized types
        kwargs["bases"] = cls.__bases__
        hydrated_cls = make_dataclass(cls.__name__, new_fields, **kwargs)

        # Add to the hydra store
        ConfigStore().store(cls.__name__, hydrated_cls)

        return hydrated_cls

    if cls is None:
        return wrapper
    return wrapper(cls)


@config_wrapper
class MjCambrianBaseConfig(MjCambrianDictConfig):
    """Base config for all configs.

    NOTE: This class inherits from MjCambrianDictConfig which is a subclass of
    DictConfig. There are issues with inheriting from DictConfig and instantiating an
    instance using the hydra instantiate or omegaconf.to_object methods. So these
    classes aren't meant to be instantiated, but are used for type hinting and
    validation of the config files.

    Attributes:
        custom (Optional[Dict[Any, str]]): Custom data to use. This is useful for
            code-specific logic (i.e. not in yaml files) where you want to store
            data that is not necessarily defined in the config.
    """

    custom: Optional[Dict[str, Any]] = field(default_factory=dict)


# =============================================================================
# OmegaConf resolvers


def register_new_resolver(*args, replace: bool = True, **kwargs):
    """Wrapper around OmegaConf.register_new_resolver to register a new resolver.
    Defaults to replacing the resolver if it already exists (opposite of the default
    in OmegaConf)."""
    OmegaConf.register_new_resolver(*args, replace=replace, **kwargs)


def search(
    key: str | None = None,
    /,
    mode: Optional[str] = "value",
    *,
    depth: int = 0,
    _parent_: DictConfig,
) -> Any:
    """This method will recursively search up the parent chain for the key and return
    the value. If the key is not found, will raise a KeyError.

    For instance, a heavily nested value might want to access a value some level
    higher but it may be hazardous to use relative paths (i.e. ${..key}) since
    the config may be changed. Instead, we'll search up for a specific key to set the
    value to. Helpful for setting unique names for an object in a nested config.

    NOTE: This technically uses hidden attributes (i.e. _parent).

    Args:
        key (str | None): The key to search for. Could be none (like when mode is
            "parent_key").
        mode (Optional[str]): The mode to use. Defaults to "value". Available modes:
            - "value": Will return the value of the found key. Key must be set.
            - "parent_key": Will return the parent's key. If key is None, won't do
                any recursion and will return the parent's key.
        depth (int, optional): The depth of the search. Used internally
            in this method and unsettable from the config. Avoids checking the parent
            key.
        _parent_ (DictConfig): The parent config to search in.
    """
    if _parent_ is None:
        # Parent will be None if we're at the top level
        raise KeyError(f"Key {key} not found in parent chain.")

    if mode == "value":
        if key in _parent_:
            # If the key is in the parent, we'll return the value
            return _parent_[key]
        else:
            # Otherwise, we'll keep searching up the parent chain
            return search(key, mode=mode, depth=depth + 1, _parent_=_parent_._parent)
    elif mode == "parent_key":
        if key is None:
            # If the key is None, we'll return the parent's key
            assert _parent_._key() is not None, "Parent key is None."
            return _parent_._key()

        if depth != 0 and isinstance(_parent_, DictConfig) and key in _parent_:
            # If we're at a key that's not the parent and the parent has the key we're
            # looking for, we'll return the parent
            return search(None, mode=mode, depth=depth + 1, _parent_=_parent_)
        else:
            # Otherwise, we'll keep searching up the parent chain
            return search(key, mode=mode, depth=depth + 1, _parent_=_parent_._parent)


register_new_resolver("search", search)
register_new_resolver("parent", partial(search, mode="parent_key"))
register_new_resolver("eval", eval)

# =============================================================================
# Utilities for config loading


def instance_wrapper(instance: Type[Any], **kwargs):
    """This utility method will wrap a class instance to help with setting class
    attributes after initialization.

    Some classes, for instance, don't include all attributes in the constructor; this
    method will postpone setting these attributes until after __init__ is called and
    just set the attributes directly with setattr.

    This is intended to be called from a yaml config file like so:

    ```yaml
    obj_to_instantiate:
        _target_: <path_to>.instance_wrapper
        instance:
            _target_: <class>

            # these will be passed to the __init__ method
            _args_: [arg1, arg2]

            # these will be passed to the __init__ method as kwargs
            init_arg1: value1
            init_arg2: value2

        # these will be set as attributes after the __init__ method
        set_arg1: value1
        set_arg2: value2
    ```

    At instantiate time, init args are not always known. As such, you can leverage
    hydras partial instantiation logic, as well. Under the hood, the instance_wrapper
    method will wrap the partial instance created by hydra such that when it's
    constructor is actually called, the attributes will be set.

    ```yaml
    partial_obj_to_instantiate:
        _target_: <path_to>.instance_wrapper
        instance:
            _target_: <class>
            _partial_: True

            # these will be passed to the __init__ method
            _args_: [arg1, arg2]

            # these will be passed to the __init__ method as kwargs
            init_arg1: value1
            init_arg2: value2
            init_arg3: '???' # this is unknown at instantiate time and can be set later

        # these will be set as attributes after the __init__ method
        set_arg1: value1
        set_arg2: value2
    ```

    Args:
        instance (Type[Any]): The class instance to wrap.

    Keyword Args:
        kwargs: The attributes to set on the instance.
    """

    def setattrs(instance, **kwargs):
        try:
            for key, value in kwargs.items():
                setattr(instance, key, value)
        except Exception as e:
            raise ValueError(f"Error when setting attribute {key=} to {value=}: {e}")
        return instance

    if isinstance(instance, partial):
        # If the instance is a partial, we'll setup a wrapper such that once the
        # partial is actually instantiated, we'll set the attributes of the instance
        # with the kwargs.
        partial_instance = instance
        config_kwargs = kwargs

        def wrapper(*args, **kwargs):
            # First instantiate the partial
            instance = partial_instance(*args, **kwargs)
            # Then set the attributes
            return setattrs(instance, **config_kwargs)

        return wrapper
    else:
        return setattrs(instance, **kwargs)


def instance_flag_wrapper(instance: Type[Any], key: str, flag_type: Type[Any], **flags):
    """This utility method will wrap a class instance to help with setting class
    attributes after initialization. As opposed to instance_wrapper, this method will
    set attribute flags on the instance. This is particularly useful for mujoco enums,
    which are stored in a list.

    This is intended to be called from a yaml config file and to be used in conjunction
    with the instance_wrapper method.

    ```yaml
    obj_to_instantiate:
        _target_: <path_to>.instance_wrapper
        instance:
            _target_: <class>

        # these will be set as flags on the instance
        flags:
            _target_: <path_to>.instance_flag_wrapper
            instance: ${..instance}                     # get the instance
            key: ${parent:}                             # gets the parent key; "flags"
            flag_type:
                _target_: <class>                       # the class of the flag

            # These will be set like so:
            # obj_to_instaniate.key[flag1] = value1
            # obj_to_instaniate.key[flag2] = value2
            # ...
            flag1: value1
            flag2: value2
            flag3: value3
    ```

    This also works for partial instances.

    Args:
        instance (Type[Any]): The class instance to wrap.
        key (str): The key to set the flags on.
        flag_type (Type[Any]): The class of the flag.

    Keyword Args:
        flags: The flags to set on the instance.
    """

    def setattrs(instance, key, flag_type, **flags):
        """Set the attributes on the instance."""
        attr = getattr(instance, key)
        for flag, value in flags.items():
            flag = getattr(flag_type, flag)
            attr[flag] = value
        return attr

    if isinstance(instance, partial):
        partial_instance = instance
        config_key = key
        config_type = flag_type
        config_flags = flags

        def wrapper(*args, **kwargs):
            # First instantiate the partial
            instance = partial_instance(*args, **kwargs)
            # Then set the attributes
            return setattrs(instance, config_key, config_type, **config_flags)

        return wrapper
    else:
        return setattrs(instance, key, flag_type, **flags)