from importlib.resources import files

from langchain_core.prompts import ChatPromptTemplate
from langchain_openai import ChatOpenAI

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
        (
            "human",
            files(prompts).joinpath("quiz_extraction_prompt.txt").read_text()
            + "\n\nContent:\n{text}",
        ),
    ]
)


def get_model(model_name):
    return ChatOpenAI(model=model_name or "gpt-4o-mini").with_structured_output(
        Quiz, method="json_mode"
    )


def quiz2queck(quiz: Quiz):
    return Queck.model_validate(
        quiz.model_dump(
            context={"formatted": True}, exclude_none=True, exclude_defaults=True
        )
    )


def prompt_queck(prompt: str, model_name: None):
    model = get_model(model_name)
    quiz_extraction_chain = quiz_extraction_prompt | model
    return quiz2queck(quiz_extraction_chain.invoke({"text": prompt}))


def extract_queck(file_name, model_name=None):
    model = get_model(model_name)
    quiz_extraction_chain = quiz_extraction_prompt | model
    with open(file_name) as f:
        content = f.read()
    quiz = quiz_extraction_chain.invoke({"text": content})
    return quiz2queck(quiz=quiz)
