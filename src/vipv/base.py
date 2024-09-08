from typing import Dict, List

from pydantic import BaseModel, Field


class Hunch(BaseModel):
    """Testable hypothesis :)"""

    one_liner: str = Field(alias="oneLiner")


class ValidationMetadata(BaseModel):
    """Model representing additonal information
    in a validation"""

    version: str
    hunches: List[Hunch]


class DecodingParameters(BaseModel):
    """Model-specific decoding parameters to pass

    *NOTE:* This does not support all of the parameters that might be supported
    in a given model
    """

    temperature: float = 0.0


class ModelSpec(BaseModel):

    model: str
    decoding_parameters: DecodingParameters = Field(alias="decodingParameters")


class InterviewMetadata(BaseModel):
    annotations: Dict[
        str,
        str,
    ]


class InterviewSpec(BaseModel):
    """Plan for how an interview should be conducted and
    what the intended questions and learnings are
    """

    biggest_intended_learning: str = Field(alias="biggestIntendedLearning")
    questions: List[str]
    max_num_steps: int = Field(
        default=10,
        alias="maxNumSteps",
    )


class Interview(BaseModel):
    """Top-level container for interview specification and
    associated metadata
    """

    metadata: InterviewMetadata
    spec: InterviewSpec


class Persona(BaseModel):
    """Definition of a persona you want to query to learn
    and test your hypotheses
    """

    title: str
    job_description: str = Field(alias="jobDescription")
    specific_expertise: str = Field(alias="specificExpertise")


class Experiment(BaseModel):
    """Model representing an interview on a specific persona, run for a given number of steps"""

    persona: Persona
    interview: Interview
    llm_spec: ModelSpec = Field(alias="llmSpec")

    num_repeats: int = Field(
        default=1,
        alias="numRepeats",
    )


class ValidationRun(BaseModel):
    """Top-level model for a validation. It defines what your hypotheses (hunches)
    are, what your idea is, what your target personas are, what you want to learn, and
    where to write the output.

    This is taken up by a driver process which is set using a system prompt defined
    to set the context (follow your hunches) It then goes on and pretends it is you, collecting
    information from other instances of the model pretending they are the persona you want
    to interview.
    """

    idea: str
    metadata: ValidationMetadata
    experiments: List[Experiment]
    output_dir: str = Field(alias="outputDir")


class InterviewTurn(BaseModel):
    interviewer: str
    persona: str


InterviewOutput = List[InterviewTurn]


class ExperimentOutput(BaseModel):
    persona: str
    interviews: List[InterviewOutput]


class ValidationRunOutput(BaseModel):
    idea: str
    metadata: ValidationMetadata
    experiment_output: List[ExperimentOutput]
