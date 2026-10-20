"""CLI for validating and running named experiment configurations."""
import argparse
from config.loader import load_catalog, resolve_experiment
from backtesting.runner import run_experiment


def main() -> None:
    parser = argparse.ArgumentParser(description="Run configuration-driven AlgoTrade experiments.")
    parser.add_argument("--config-dir", default="config", help="Directory containing YAML catalogs")
    commands = parser.add_subparsers(dest="command", required=True)
    commands.add_parser("list", help="List configured experiments")
    validate = commands.add_parser("validate", help="Validate an experiment without running it")
    validate.add_argument("--experiment", required=True)
    run = commands.add_parser("run", help="Run one named experiment")
    run.add_argument("--experiment", required=True)
    args = parser.parse_args()
    catalog = load_catalog(args.config_dir)
    if args.command == "list":
        for name, definition in catalog["experiments"].items():
            print(f"{name}: {definition.get('description', '')}")
    elif args.command == "validate":
        experiment = resolve_experiment(catalog, args.experiment)
        print(f"Experiment '{args.experiment}' is valid.")
        print(f"Datasets: {', '.join(experiment['datasets'])}")
        print(f"Strategies: {', '.join(experiment['strategies'])}")
        print(f"Combinations: {len(experiment['datasets']) * len(experiment['strategies'])}")
    else:
        result = run_experiment(catalog, args.experiment)
        print(f"Summary: {result['summary_path']}")
        print(f"Report: {result['report_path']}")


if __name__ == "__main__":
    main()
