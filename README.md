# PyKen x Plutuscope

PyKen x Plutuscope is a toolkit for building Python-style Aiken smart contracts (**PyKen**) and debugging them with a powerful validator simulation and trace explorer (**Plutuscope**).

---

## Project structure

- `Aiken Validators/` — Smart contracts and Validators written in Aiken.
- `PyKen/` — Transpilation framework (Python → Aiken).
- `Plutuscope/` — Debugger, simulator, and trace explorer.
- `docs/` — Extended project documentation and design notes.

---

## Architecture overview

### PyKen — Transpilation framework

PyKen translates Python-style validator logic into Aiken smart contracts for Cardano.

Main modules

- `py_parser.py` — Parse Python functions (AST → function metadata).
- `py_validator.py` — Wrap parsed functions into validator scaffolding.
- `validator_emitter.py` — Walk AST and emit Aiken source (imports, types, pattern matching, assertions, simple control flow, and more).
- `transpile.py` — Entry script: read Python files, transpile, and write `.ak` output.

Support libraries (helpers)

- `mocktail.py`, `cocktail.py` — local transaction builder and test helpers used by examples.
- `aiken/*`, `cardano/*` — type mirrors to make writing Python validators feel similar to Aiken.
- `decorators.py` — decorator helpers (e.g., `@validator`) used by example code.

---

### Plutuscope — Validator narration & simulation

Plutuscope is a CLI tool for exploring Aiken validator projects. It supports trace collection, rendering traces as trees, and basic simulation for narrative inspection.

Features

- Trace collection — read output from `aiken check`, parse logs, or use synthesized traces created by instrumentation.
- Trace rendering — interactive tree view of execution with pass/fail markers.
- Validator narration — human-readable explanations of common validator constructs.
- Simulation — optional simulated execution of simple paths to produce traces.
- Test mapping — heuristics to map tests to validator functions in example harnesses.

CLI usage examples

```bash
# Scan for validators in a project
python plutuscope.py --scan path\to\project

# Narrate a single validator
python plutuscope.py --aiken contracts/my_validator.ak --simulate

# Instrument project and synthesize traces
python plutuscope.py --aiken path\to\project --simulate --instrument --verbose
```

---

## Examples

Open the `PyKen/Examples/` folder to find small Python validators and mock transactions. The examples use helper modules so you can run them without a full Cardano node.

---

## Setup

Prerequisites

- [Aiken](https://aiken-lang.org) installed.
- Python 3.10+ installed.
- Install Python dependencies:

```bash
pip install -r requirements.txt

pip install Rich
```

---

## Deployment

Compile Smart Contracts

```bash
aiken build
```

Run Tests

```bash
aiken check
```

---

## Simulation and Debugging

Use Plutuscope to simulate and debug validators:

```bash
# Narrate a validator with simulation
python plutuscope.py --aiken contracts/my_validator.ak --simulate

# Verbose simulation with instrumentation
python plutuscope.py --aiken validators/ --simulate --verbose --instrument
```

---

## Documentation

[PyKen x Plutuscope Documentation](docs/PyKen_x_Plutuscope_Documentation.pdf)

---

## Contributing

This project is early-stage and welcomes contributions. Please open issues for bugs or feature requests and send PRs for improvements.

---

## License

[LICENSE](LICENSE)
