import json
import re
from functools import wraps
from importlib.resources import files

from pydantic import ValidationError
from pydantic.json_schema import GenerateJsonSchema, JsonSchemaValue

from . import prompts
from .model_utils import yaml_dump
from .queck_models import Queck
from .quiz_models import Quiz

GENAI_ENABLED = True
try:
    from langchain.chat_models import init_chat_model
    from langchain_core.output_parsers import StrOutputParser
    from langchain_core.prompts import ChatPromptTemplate
    from langchain_core.runnables import RunnableLambda
except ImportError:
    GENAI_ENABLED = False

if GENAI_ENABLED:
    quiz_generation_prompt = ChatPromptTemplate(
        [
            ("system", files(prompts).joinpath("quiz_structure.txt").read_text()),
            ("human", "{prompt}"),
        ]
    )

    quiz_extraction_prompt = ChatPromptTemplate(
        [
            ("system", files(prompts).joinpath("quiz_structure.txt").read_text()),
            (
                "human",
                files(prompts).joinpath("quiz_extraction_prompt.txt").read_text(),
            ),
        ]
    )


def genai_feature_check_wrapper(func):
    @wraps(func)
    def inner(*args, **kwargs):
        if GENAI_ENABLED:
            return func(*args, **kwargs)
        else:
            print(
                "This feature requires genai extras for this package. "
                "Please install the package as "
                "queck[genai] or queck[all] to avail this feature."
            )

    return inner


def remove_defaults(schema: dict) -> dict:
    if isinstance(schema, dict):
        return {k: remove_defaults(v) for k, v in schema.items() if k != "default"}
    elif isinstance(schema, list):
        return [remove_defaults(item) for item in schema]
    return schema


class NoDefaultJsonSchema(GenerateJsonSchema):
    def generate(self, schema, mode="validation") -> JsonSchemaValue:
        original_schema = super().generate(schema, mode=mode)
        cleaned_schema = remove_defaults(original_schema)
        return cleaned_schema


@genai_feature_check_wrapper
def get_validator(force_single_select=False):
    return RunnableLambda(
        lambda x: Quiz.model_validate(
            x,
            context={
                "fix_multiple_select": True,
                "force_single_select": force_single_select,
                "ignore_n_correct": True,
            },
        )
    )


def json_extract(x):
    """Utility to remove code blocks from LLM output if exists."""
    x = re.match(
        r"(```[^\n]*\n)?(?P<content>\{.*\})(\n```)?", x.strip(), re.DOTALL
    ).groupdict()["content"]
    return json.loads(x)


@genai_feature_check_wrapper
def get_model(model_name):
    model_provider, model_name = model_name.split(":")
    if model_provider == "openai":
        return init_chat_model(
            model=model_name, model_provider=model_provider
        ).with_structured_output(Quiz.model_json_schema(), method="json_schema")
    elif model_provider == "groq":
        return init_chat_model(
            model=model_name,
            model_provider=model_provider,
        ).with_structured_output(Quiz.model_json_schema(), method="json_mode")
    elif model_provider == "google_genai":
        return (
            init_chat_model(
                model=model_name,
                model_provider=model_provider,
            )
            | StrOutputParser()
            | RunnableLambda(json_extract)
        )


def quiz2queck(
    quiz: Quiz,
    ignore_n_correct: bool = True,
    force_single_select: bool = True,
    fix_multiple_select: bool = True,
):
    quiz_dump = quiz.model_dump(
        context={"formatted": True}, exclude_none=True, exclude_defaults=True
    )
    try:
        return Queck.model_validate(
            quiz_dump,
            context={
                "fix_multiple_select": fix_multiple_select,
                "force_single_select": force_single_select,
                "ignore_n_correct": ignore_n_correct,
            },
        )
    except ValidationError as e:
        e.args = (quiz_dump,)
        raise e


@genai_feature_check_wrapper
def prompt_queck(prompt: str, model_name: None):
    model = get_model(model_name)

    quiz_extraction_chain = quiz_extraction_prompt | model | get_validator()
    return quiz2queck(quiz_extraction_chain.invoke({"text": prompt}))


@genai_feature_check_wrapper
def extract_queck(
    file_name: str,
    model: str | None = None,
    prompt_extra: str | None = None,
    force_single_select: bool = True,
    output_file: str | None = None,
):
    """Extracts the questions as queck from the given file.

    Args:
        file_name (str): The source file to extract.
        model (str):
            The model of format "provider:model".
            Supported providers are "openai", "groq" and "google_genai".
        prompt_extra (str): Any additional instructions for extraction.
        force_single_select (bool):
            Whether to force question to single select if there
            is only one correct option.
        output_file (str): File name for the output.
    """
    try:
        model_chain = get_model(model)
        quiz_extraction_chain = (
            quiz_extraction_prompt.partial(prompt_extra=prompt_extra)
            | model_chain
            | get_validator(force_single_select=force_single_select)
        )
        with open(file_name) as f:
            content = f.read()
        queck = quiz2queck(quiz=quiz_extraction_chain.invoke({"text": content}))
        if output_file is None:
            return queck
        else:
            queck.to_queck(output_file)

    except Exception as e:
        if e.args:
            yaml_dump(e.args[0], output_file, extension="qk")
        raise e
