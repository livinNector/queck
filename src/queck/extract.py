from importlib.resources import files

from langchain_core.prompts import ChatPromptTemplate
from langchain_openai import ChatOpenAI

from . import prompts
from .queck_models import Queck
from .quiz_models import Quiz

quiz_extraction_prompt = ChatPromptTemplate(
    [
        ("system", files(prompts).joinpath("quiz_extraction_prompt.txt").read_text()),
        ("human", "Content:\n{text}"),
    ]
)


def extract_queck(file_name, model=None):
    model = ChatOpenAI(model=model or "gpt-4o-mini").with_structured_output(
        Quiz, method="json_mode"
    )
    quiz_extraction_chain = quiz_extraction_prompt | model
    with open(file_name) as f:
        content = f.read()
    quiz: Quiz = quiz_extraction_chain.invoke({"text": content})
    return Queck.model_validate(
        quiz.model_dump(
            context={"formatted": True}, exclude_none=True, exclude_defaults=True
        )
    )
