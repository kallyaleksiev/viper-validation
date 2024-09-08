import asyncio
from typing import Optional

import click
import yaml

from vipv.base import ValidationRun
from vipv.logging_utils import get_logger
from vipv.runners import ValidationRunRunner

logger = get_logger(__name__)


@click.command()
@click.option(
    "-f",
    "--filename",
    required=True,
    type=click.Path(exists=True),
    help="Path to the YAML config file",
)
@click.option(
    "--max-concurrent-validation",
    default=1,
    type=int,
    help="Maximum concurrent validations",
)
@click.option(
    "--max-concurrent-experiment",
    default=2,
    type=int,
    help="Maximum concurrent experiments per validation",
)
@click.option(
    "-o",
    "--output-dir",
    required=False,
    type=click.Path(),
    help="Override the output directory",
)
def main(
    filename: str,
    max_concurrent_validation: int,
    max_concurrent_experiment: int,
    output_dir: Optional[str],
):
    logger.info(f"Reading config file {filename}...")
    with open(filename, "r") as f:
        config_data = yaml.safe_load(f)

    validation_run = ValidationRun.model_validate(config_data)

    # Override the output directory if provided
    if output_dir:
        logger.info(f"Overriding output dir to {output_dir}...")
        validation_run.output_dir = output_dir

    runner = ValidationRunRunner(
        validation_run=validation_run,
        max_concurrent_per_validation=max_concurrent_validation,
        max_concurrent_per_experiment=max_concurrent_experiment,
    )

    logger.info("Starting validation run...")

    async def runner_wrapper():
        _ = await runner.run()

    asyncio.run(runner_wrapper())


if __name__ == "__main__":
    main()
