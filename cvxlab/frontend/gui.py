"""Stateful guided user interface for CVXlab."""
import inspect

from pathlib import Path
from typing import Any, Callable

from cvxlab.backend.model import Model
from cvxlab.frontend import util_gui
from cvxlab.frontend.gui_defaults import Action, GuiDefaults, Parameter
from cvxlab.log_exc import exceptions as exc
from cvxlab.log_exc.exceptions import CVXLabError
from cvxlab.support import model_directory


class Gui:
    """Manage the configuration, model state, and menus of a GUI session."""

    def __init__(self, **settings: Any) -> None:
        if 'use_existing_data' in settings:
            raise exc.SettingsError(
                GuiDefaults.USE_EXISTING_DATA_CONFIGURATION)

        allowed_settings = set(GuiDefaults.MODEL_PARAMETERS) | {'action_settings'}
        invalid_settings = [
            name for name in settings
            if name not in allowed_settings
        ]
        if invalid_settings:
            raise exc.SettingsError(
                GuiDefaults.INVALID_CONFIGURATION.format(
                    names=invalid_settings)
            )

        action_settings = settings.pop('action_settings', {})
        if not isinstance(action_settings, dict) or not all(
            isinstance(name, str) and isinstance(values, dict)
            for name, values in action_settings.items()
        ):
            raise exc.SettingsError(GuiDefaults.INVALID_ACTION_SETTINGS_TYPE)

        self.model_settings = {
            name: settings.get(name)
            for name in GuiDefaults.MODEL_PARAMETERS
        }
        self.action_settings = {
            name: dict(values)
            for name, values in action_settings.items()
        }
        self.model: Model | None = None
        self._actions = self._action_mapping(GuiDefaults.MENU)
        self._validate_action_settings()

    @staticmethod
    def _action_mapping(actions: tuple[Action, ...]) -> dict[str, Action]:
        mapping = {}
        for action in actions:
            if action.children:
                mapping.update(Gui._action_mapping(action.children))
            else:
                mapping[action.name] = action
        return mapping

    def _validate_action_settings(self) -> None:
        invalid_actions = [
            name for name in self.action_settings
            if name not in self._actions
        ]
        invalid_arguments = {
            name: [
                argument for argument in values
                if argument not in self._actions[name].arguments
            ]
            for name, values in self.action_settings.items()
            if name in self._actions
        }
        invalid_arguments = {
            name: arguments
            for name, arguments in invalid_arguments.items()
            if arguments
        }

        messages = []
        if invalid_actions:
            messages.append(
                GuiDefaults.INVALID_ACTION_NAMES.format(
                    names=invalid_actions))
        if invalid_arguments:
            messages.append(
                GuiDefaults.INVALID_ACTION_SETTINGS.format(
                    settings=invalid_arguments))
        if messages:
            raise exc.SettingsError("\n".join(messages))

    def require_model(self) -> Model:
        if self.model is None:
            raise exc.SettingsError(GuiDefaults.NO_ACTIVE_MODEL)
        return self.model

    def _resolved_setting(self, name: str) -> Any:
        if name == 'main_dir_path':
            return self.model_settings[name] or str(Path.cwd())
        if name == 'model_dir_name':
            return self.model_settings[name] or 'model'
        if name == 'model_dir_path':
            return str(Path(
                self._resolved_setting('main_dir_path'),
                self._resolved_setting('model_dir_name'),
            ))
        if name == 'instance_file_name':
            return 'model_instance'
        if name == 'settings_file_type':
            return self.model_settings['model_settings_from'] or 'yml'
        return self.model_settings.get(name)

    @staticmethod
    def _signature_default(callable_: Callable, name: str) -> Any:
        parameter = inspect.signature(callable_).parameters[name]
        if parameter.default is inspect.Parameter.empty:
            return util_gui.MISSING
        return parameter.default

    def _model_arguments(
            self,
            names: tuple[str, ...] | None = None,
    ) -> dict[str, Any]:
        names = names or tuple(GuiDefaults.MODEL_PARAMETERS)
        arguments = {}
        for name in names:
            value = self.model_settings[name]
            if value is None:
                definition = GuiDefaults.MODEL_PARAMETERS[name]
                value = util_gui.ask(
                    label=definition.label,
                    default=self._signature_default(Model, name),
                    parser=definition.parser,
                    choices=definition.choices,
                )
                self.model_settings[name] = value
            arguments[name] = value
        return arguments

    def _callable(self, action: Action) -> Callable:
        if action.target == 'model':
            return getattr(self.require_model(), action.name)
        if action.target == 'model_constructor':
            return Model
        if action.target == 'model_instance':
            return model_directory.handle_model_instance
        if action.target == 'package':
            if action.name == 'installed_solvers':
                from cvxlab.defaults import Defaults
                return Defaults.NumericalSettings.get_installed_solvers
            return getattr(model_directory, action.name)
        raise RuntimeError(GuiDefaults.UNKNOWN_ACTION_TARGET.format(
            target=action.target))

    @staticmethod
    def _parameter_is_enabled(
            parameter: Parameter,
            arguments: dict[str, Any],
    ) -> bool:
        if parameter.when_parameter is None:
            return True
        return arguments.get(parameter.when_parameter) in parameter.when_values

    def _action_arguments(
            self,
            action: Action,
            callable_: Callable,
    ) -> dict[str, Any]:
        configured = self.action_settings.setdefault(action.name, {})
        arguments = {}
        if action.target == 'model_constructor':
            arguments.update(self._model_arguments())
        elif action.model_arguments:
            arguments.update(self._model_arguments(action.model_arguments))

        for name, definition in action.arguments.items():
            if not self._parameter_is_enabled(definition, arguments):
                continue
            if name in configured:
                arguments[name] = configured[name]
                continue

            label = definition.label
            if definition.model_attribute is not None:
                available = getattr(
                    self.require_model(), definition.model_attribute)
                label += f" (available: {available})"

            if definition.default_from is not None:
                default = self._resolved_setting(definition.default_from)
            else:
                default = self._signature_default(callable_, name)

            value = util_gui.ask(
                label=label,
                default=default,
                parser=definition.parser,
                choices=definition.choices,
            )
            configured[name] = value
            arguments[name] = value

        arguments.update(action.fixed_arguments)
        if action.target == 'model_instance' and action.require_model:
            arguments['instance'] = self.require_model()
        return arguments

    def _execute(self, action: Action) -> None:
        callable_ = self._callable(action)
        arguments = self._action_arguments(action, callable_)
        result = callable_(**arguments)

        if action.assign_model:
            self.model = result
        if action.print_result:
            print(result)

    def _run_menu(
            self,
            actions: tuple[Action, ...],
            is_submenu: bool = False,
    ) -> bool:
        labels = [action.label for action in actions]
        n_actions = len(actions)

        while True:
            util_gui.print_menu(labels, is_submenu)
            choice = util_gui.prompt_choice(n_actions, is_submenu).lower()

            if choice in ('q', 'quit'):
                print(GuiDefaults.EXIT_MESSAGE)
                return True
            if choice in ('b', 'back') and is_submenu:
                return False
            if not choice.isdigit() or not (1 <= int(choice) <= n_actions):
                alternatives = f"1 to {n_actions}"
                if is_submenu:
                    alternatives += ", 'back'"
                alternatives += ", or 'quit'"
                print(GuiDefaults.INVALID_SELECTION.format(
                    alternatives=alternatives))
                continue

            action = actions[int(choice) - 1]
            if action.children:
                if self._run_menu(action.children, is_submenu=True):
                    return True
                util_gui.print_separator()
                continue

            util_gui.print_log_start()
            try:
                self._execute(action)
            except KeyboardInterrupt:
                util_gui.print_log_end()
                print(GuiDefaults.INTERRUPTED_MESSAGE)
            except CVXLabError as error:
                util_gui.print_log_end()
                print(GuiDefaults.FAILED_MESSAGE.format(error=error))
            except Exception as error:
                util_gui.print_log_end()
                print(GuiDefaults.UNEXPECTED_ERROR.format(error=error))
            else:
                util_gui.print_log_end()
            util_gui.print_separator()

    def run(self) -> None:
        """Launch the menu loop for this GUI session."""
        util_gui.clear_screen()
        util_gui.print_header()
        self._run_menu(GuiDefaults.MENU)


def gui(**settings: Any) -> None:
    """Launch CVXlab's guided, menu-driven terminal interface.

    The interface provides access to the main CVXlab workflow without requiring
    each API operation to be called directly. The call blocks until the user
    quits the interface. When a value needed by a selected action has not been
    preconfigured, the interface prompts for it and retains the answer for the
    rest of the session.

    Keyword Args:
        model_dir_name (str): Name of the model directory.
        main_dir_path (str): Directory containing the model directory. If no
            value is supplied interactively, the current working directory is
            used.
        model_settings_from (str): Model-settings file format, either ``"yml"``
            or ``"xlsx"``.
        detailed_validation (bool): Whether to log detailed validation of model
            settings and data during model initialization.
        multiple_input_files (bool): Whether to use one input file per data
            table instead of a single file containing all tables.
        input_data_files_type (str): Input-data file format, either ``"xlsx"``
            or ``"csv"``.
        log_level (str): Logging level: ``"debug"``, ``"info"``,
            ``"warning"``, or ``"error"``.
        log_format (str): Logging format, either ``"standard"`` or
            ``"detailed"``.
        action_settings (dict[str, dict[str, Any]]): Values to preconfigure for
            individual menu actions. Each key is the public API action name and
            its value maps that action's argument names to values. For example,
            ``{"run_model": {"solver": "CLARABEL"}}`` configures the solver
            used by the *Run model* action. Omitted action arguments are
            requested interactively when first needed.

    Raises:
        SettingsError: If a top-level setting, action name, or action argument
            is not recognized, or if ``action_settings`` has an invalid shape.

    Example:
        Preconfigure the model location and selected run options::

            cvxlab.gui(
                model_dir_name="my_model",
                main_dir_path="/path/to/models",
                action_settings={
                    "run_model": {
                        "solution_mode": "parallel",
                        "solver": "CLARABEL",
                    },
                },
            )

    Note:
        This function does not accept an existing :class:`cvxlab.Model`
        instance. Create, open, or load a model from the *Model session* menu.
        Similarly, ``use_existing_data`` is intentionally not a keyword
        argument. *Create new Model instance* constructs a model with
        ``use_existing_data=False``; *Open existing Model environment* uses
        ``use_existing_data=True`` and loads the existing model data and
        numerical problems.
    """
    Gui(**settings).run()
