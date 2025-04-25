from importlib.resources import files

from langchain_core.prompts import ChatPromptTemplate
from langchain_core.runnables import RunnableLambda
from langchain_groq import ChatGroq
from langchain_openai import ChatOpenAI
from pydantic.json_schema import GenerateJsonSchema, JsonSchemaValue

from . import prompts
from .queck_models import Queck
from .quiz_models import Quiz

quiz_generation_prompt = ChatPromptTemplate(
    [
        ("system", files(prompts).joinpath("quiz_structure.txt").read_text()),
        ("human", "{prompt}"),
    ]
)

quiz_extraction_prompt = ChatPromptTemplate(
    [
        ("system", files(prompts).joinpath("quiz_structure.txt").read_text()),
        ("human", files(prompts).joinpath("quiz_extraction_prompt.txt").read_text()),
    ]
)


def remove_defaults(schema: dict) -> dict:
    if isinstance(schema, dict):
        return {k: remove_defaults(v) for k, v in schema.items() if k != "default"}
    elif isinstance(schema, list):
        return [remove_defaults(item) for item in schema]
    return schema


class NoDefaultJsonSchema(GenerateJsonSchema):
    def generate(self, schema, mode: str = "validation") -> JsonSchemaValue:
        original_schema = super().generate(schema, mode=mode)
        cleaned_schema = remove_defaults(original_schema)
        return cleaned_schema


def get_model(model_name):
    model_name = model_name or "open-ai:gpt-4o-mini"
    provider, model_name = model_name.split(":")
    if provider == "open-ai":
        return ChatOpenAI(model=model_name or "gpt-4o-mini").with_structured_output(
            Quiz.model_json_schema(schema_generator=NoDefaultJsonSchema),
            method="json_schema",
        )
    elif provider == "groq":
        return ChatGroq(
            model=model_name or "llama-3.1-8b-instant"
        ).with_structured_output(Quiz.model_json_schema(), method="json_mode")


def get_validator(fix_multi_select=True, force_single_select=False):
    return RunnableLambda(
        lambda x: Quiz.model_validate(
            x,
            context={
                "fix_multi_select": fix_multi_select,
                "force_single_select": force_single_select,
            },
        )
    )


def quiz2queck(quiz: Quiz):
    return Queck.model_validate(
        quiz.model_dump(
            context={"formatted": True}, exclude_none=True, exclude_defaults=True
        )
    )


def prompt_queck(prompt: str, model_name: None):
    model = get_model(model_name)

    quiz_extraction_chain = quiz_extraction_prompt | model | get_validator()
    return quiz2queck(quiz_extraction_chain.invoke({"text": prompt}))


def extract_queck(file_name, model_name=None, force_single_select=True):
    model = get_model(model_name)
    quiz_extraction_chain = (
        quiz_extraction_prompt
        | model
        | get_validator(force_single_select=force_single_select)
    )
    with open(file_name) as f:
        content = f.read()
    quiz = quiz_extraction_chain.invoke({"text": content})
    return quiz2queck(quiz=quiz)
