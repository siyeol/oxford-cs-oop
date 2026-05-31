# Project: Marketplace Backend

The purpose of this project is to implement a Python 3.14 library — for educational purposes only — implementing a backend for a marketplace system.
For your context, you can find information about the marketplace specifications in the `SPECIFICATIONS.md` file.

The package root is `marketplace`, and you can find project information in `pyproject.toml`.

## Workflow

- You will implement small components (one or few functions/methods at a time) according to my design and specification.
- Implement exactly what I tell you to. Do not take initiative. You are just helping me with writing code I already know how to write.
- When I ask you to create a module, create a blank module with a module docstring only.
- When I ask you to create a class, create a blank class with a class docstring and slots (see below).
- When I ask you to create a function/method, create a blank function/method with a docstring and `raise NotImplementedError()` as body.

## Style

- All code should be compliant with Mypy --strict and should use Python 3.14 style types.
- Do not stringify forward-reference annotations. Python 3.14 evaluates annotations lazily (PEP 649), so forward references to classes defined later in the same module can be written as bare names (e.g. `-> ActiveListing`) rather than strings (e.g. `-> "ActiveListing"`).
- When using collection types, always prefer `collections.abc` to `typing`.
- To create a `TypedDict` value, use a dict literal with an explicit annotation (e.g. `info: CompleteListingInfo = {"title": ..., ...}`), not the TypedDict class constructor call.
- Format code using `black`, no additional options.
- Do not leave blank lines in function bodies.
- Do not introduce comments unless I explicitly tell you to. In particular, no section comments.
- For constructors, always use `__new__` with `Self` return type. Do not use `__init__`. If it is strictly necessary to use `__init__` (e.g. for complex multiple inheritance) I will instruct you to do so explicitly.
- When calling superclass constructors, never use `super()`, always use explicit class name.
- Instance and class attributes should always be explicitly annotated.
- Classes should always use slots. Include `__weakref__` for classes at the top of their inheritance hierarchy. Include all annotated attributes in the slots.

## Agent Self-improvement

- You are allowed to modify `CLAUDE.md` to keep track of my evolving preferences and requirements.
