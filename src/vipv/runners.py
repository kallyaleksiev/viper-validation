import asyncio
import copy
import os
from asyncio import Semaphore
from datetime import datetime
from typing import List, cast

import anthropic
from anthropic.types import MessageParam, TextBlock

from vipv.base import (
    Experiment,
    ExperimentOutput,
    Hunch,
    InterviewOutput,
    InterviewTurn,
    ValidationRun,
    ValidationRunOutput,
)
from vipv.logging_utils import get_logger

logger = get_logger(__name__)


class ExperimentRunner:
    """Class that runs one user experiment (list of interviews) flow

    It constructs two system prompts -- one for interviewer and one for persona.
    It then reuses a client to a specific model to generate quesitons,
    answer pairs from the model
    """

    def __init__(
        self,
        idea: str,
        experiment: Experiment,
        hunches: List[Hunch],
        max_num_concurrent: int = 8,
    ):
        self._idea = idea
        self._experiment = experiment
        self._hunches = hunches
        self._max_num_concurrent = max_num_concurrent

        # reuse this client across calls
        if "ANTHROPIC_API_KEY" not in os.environ:
            raise RuntimeError("Must specify LLM api key via env variable")

        self.client = anthropic.AsyncAnthropic()

        # set up the system prompts
        self.persona_system_prompt = (
            f"You are {self._experiment.persona.title}. "
            f"Your specific responsibilities include "
            f"{self._experiment.persona.job_description}, but also anything that can "
            f"reasonably be inferred from your job title. You happen to possess "
            f"the following specific expertise: {self._experiment.persona.specific_expertise}. "
            "However, the specific expertise is not something to necessarily demonstrate. "
            "You will be asked a series of research questions on an idea. "
            "Be mindful and answer truthfully but naturally, with as much interesting "
            "insight as possible. Please note the requirement to answer in a natural "
            "manner. DO NOT overcompensate or focus too much on the specific expertise "
            "unless it is useful for the answer."
        )

        hunches_str = "\n".join(map(lambda h: h.one_liner, self._hunches))
        self.interviewer_system_prompt = (
            f"You are an ambitious founder aiming to learn as much as possible. "
            f"The idea you are currently exploring is {self._idea}. You have the following "
            f"hypotheses about the space: {hunches_str}. Another key thing you want to learn "
            f"is {self._experiment.interview.spec.biggest_intended_learning}, but you should "
            "not compromise the quality of the questions by asking "
            "something directly about that. "
            "You are conducting a Mom Test-style interview to "
            "validate your idea and hunches. "
            "Your task is to come up with the best possible questions "
            "to continue the conversation. "
            "You will be tasked with either follow-up questions or "
            "selecting the most useful questions."
        )

    async def _model_call(
        self,
        conversation: List[MessageParam],
        *,
        is_persona: bool,
    ) -> str:
        response = await self.client.messages.create(
            model=self._experiment.llm_spec.model,
            temperature=self._experiment.llm_spec.decoding_parameters.temperature,
            max_tokens=512,
            system=(
                self.persona_system_prompt
                if is_persona
                else self.interviewer_system_prompt
            ),
            messages=conversation,
        )

        return cast(TextBlock, response.content[0]).text

    async def _run_interview(
        self,
    ) -> InterviewOutput:
        interview_output: InterviewOutput = []
        running_conversation: List[MessageParam] = []

        remaining_questions = set(
            copy.deepcopy(self._experiment.interview.spec.questions)
        )

        logger.info(f"Running interview with persona {self._experiment.persona.title}")

        while remaining_questions:
            questions_str = "\n".join(remaining_questions)

            if not running_conversation:
                # if first question, come up with a slightly different prompt
                prompt = (
                    f"Come up with a first question from the list to ask. "
                    "The list is as follows: "
                    f"\n{questions_str}\nDirectly copy the chosen question as your answer. "
                    "NOTE: This is the first question, so start appropriately."
                )
            elif self._experiment.interview.spec.max_num_steps - len(
                interview_output
            ) <= len(remaining_questions):
                # if there is not enough time, just ask all questions
                prompt = None
            else:
                prompt = (
                    f"Based on the conversation so far, select either one of the leftover questions "
                    "or come up with a suitable follow-up question to the previous statement. Please "
                    "be mindful that you are doing a Mom-test style interview, so you need to dive "
                    "deeper if there is signal you feel needs to be explored. That said, if the "
                    "answer is clear and there is nothing more to be said about the topic, move on "
                    f"to one of the leftover questions. The leftover questions are:\n{questions_str}\n"
                    "Directly output the chosen question as your answer, whether it's a follow-up or "
                    "from the leftover ones."
                )

            # come up with the next question
            if prompt is not None:
                suggest_question_messages = running_conversation + [
                    MessageParam(content=prompt, role="user")
                ]
                suggested_question = await self._model_call(
                    conversation=suggest_question_messages, is_persona=False
                )
            else:
                suggested_question = remaining_questions.pop()

            logger.info(
                f"Interview with persona {self._experiment.persona.title}, next question: {suggested_question}"
            )
            # bookeeping -- add the question to the running conversation and remove from the list of lefotver questions
            # if it was not a follow-up
            running_conversation.append(
                MessageParam(content=suggested_question, role="user")
            )
            remaining_questions.discard(suggested_question)

            # get the answer from the persona
            answer = await self._model_call(
                conversation=running_conversation,
                is_persona=True,
            )
            running_conversation.append(MessageParam(content=answer, role="assistant"))

            interview_output.append(
                InterviewTurn.model_validate(
                    {
                        "interviewer": suggested_question,
                        "persona": answer,
                    }
                )
            )

        return interview_output

    async def run(
        self,
    ) -> ExperimentOutput:

        async def _run_interview_bounded(semaphore: Semaphore):
            async with semaphore:
                interview_resp = await self._run_interview()

            return interview_resp

        semaphore = Semaphore(self._max_num_concurrent)
        interviews: List[InterviewOutput] = await asyncio.gather(
            *[
                _run_interview_bounded(semaphore)
                for _ in range(self._experiment.num_repeats)
            ]
        )

        return ExperimentOutput.model_validate(
            {"persona": self._experiment.persona.title, "interviews": interviews}
        )


class ValidationRunRunner:
    """Class responsible for running one validation run consisting of
    multiple experiments
    """

    def __init__(
        self,
        validation_run: ValidationRun,
        max_concurrent_per_validation: int = 4,
        max_concurrent_per_experiment: int = 8,
    ):
        self._validation_run = validation_run
        self.max_concurrent_per_validation = max_concurrent_per_validation
        self.max_concurrent_per_experiment = max_concurrent_per_experiment

        self.experiment_runners: List[ExperimentRunner] = []
        for experiment in self._validation_run.experiments:
            self.experiment_runners.append(
                ExperimentRunner(
                    idea=self._validation_run.idea,
                    experiment=experiment,
                    hunches=self._validation_run.metadata.hunches,
                    max_num_concurrent=self.max_concurrent_per_experiment,
                )
            )

    async def run(
        self,
    ) -> ValidationRunOutput:
        """Run the experiments and write the output to the specified output directory"""

        async def helper_run(experiment_runner, semaphore):
            async with semaphore:
                output = await experiment_runner.run()

            return output

        semaphore = Semaphore(self.max_concurrent_per_validation)
        experiment_outputs: List[ExperimentOutput] = await asyncio.gather(
            *[helper_run(e, semaphore) for e in self.experiment_runners]
        )

        validation_run_out = ValidationRunOutput.model_validate(
            {
                "idea": self._validation_run.idea,
                "metadata": self._validation_run.metadata,
                "experiment_output": experiment_outputs,
            }
        )

        now_str = datetime.now().strftime("%d-%m-%Y-%H:%M:%S")
        validation_run_out_name = f"validation_run_{now_str}"
        validation_run_out_file = os.path.join(
            self._validation_run.output_dir, validation_run_out_name
        )

        os.makedirs(self._validation_run.output_dir, exist_ok=True)

        logger.info(f"Validation Run done. Saving to {validation_run_out_file}...")
        with open(validation_run_out_file, "w") as f:
            f.write(validation_run_out.model_dump_json(by_alias=True))

        return validation_run_out
