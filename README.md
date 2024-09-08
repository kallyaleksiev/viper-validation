## 🎭 Viper-Validate: Mom-test style idea validator with LLMs

`vipv` is a tool for running quick, [Mom test](https://www.momtestbook.com/) style validations on your ideas using LLMs that simulate specific personas.

You define your ideas and hunches in a structured way via a yaml config.

This is just for fun to quickly explore the LLM's knowledge space. It's obviously not a substitute for the real thing but can be valuable to suggest ideas, directions, and learnings.

### Purpose

- Helps you define ideas, hunches, and intended personas in a clear way
- Quickly explore LLMs' knowledge for relevant signals
- Simulate conversations with target personas that have specific knowledge 
- Run a bunch of interviews with the LLM concurrently


### Installation

It's recommended to use [`poetry`](https://python-poetry.org/docs/)

You must also add your `ANTHROPIC_API_KEY` as env variable. 

When you have poetry just:

```
poetry install 
poetry shell 

# optionally: export ANTHROPIC_API_KEY=...

vipv -f example-schema.yaml \
    -o /Users/kally/validation-runs/ \
    --max-concurrent-validation 2 \
    --max-concurrent-experiment 2
```

### Guides and help

##### Example

1. Example schema that shows how to define personas, ideas, hunches, and interview flow is int he [yaml config](example-schema.yaml). The full type definitions are [here](src/vipv/base.py)

2. Example notebook from a run and displaying the info can be found [here](example.ipynb)

##### Help

```
Usage: vipv [OPTIONS]

Options:
  -f, --filename PATH             Path to the YAML config file  [required]
  --max-concurrent-validation INTEGER
                                  Maximum concurrent validations
  --max-concurrent-experiment INTEGER
                                  Maximum concurrent experiments per
                                  validation
  -o, --output-dir PATH           Override the output directory
  --help                          Show this message and exit.
```

