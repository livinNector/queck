# 🌟 Queck: An YAML based Format for Quiz Authoring

**Queck** is a simple and structured format for authoring quizzes based on **YAML** and **Markdown**. It provides a flexible schema for different types of questions, supporting both basic and complex quiz designs. Queck can export quizzes into **HTML** or **Markdown**, with options for live watching and automatic re-exporting upon file changes.

---

## 🆚 Alternatives

- **GIFT** – A widely used Moodle format for quiz authoring, but with more complex syntax compared to Queck’s simple YAML structure.

---

## 🔑 Key Features

- 📝 **YAML-based quiz authoring**: Author quizzes in a clean, human-readable YAML format.
- 🧠 **Support for diverse question types**: Including multiple-choice, true/false, numerical answers, comprehension passages, and more.
- ✔️ **Multiple answer formats**: Single select, multiple select, numerical ranges, and tolerance-based answers.
- 🔍 **Schema validation with Pydantic and Json Schema**: Ensures your quiz structure is validated for correctness before exporting.
- 📤 **Flexible export options**: Export quizzes in **JSON**, **HTML** (print-ready), or **Markdown** formats.
- ⚙️ **Command-line interface**: Simple CLI for validation and export operations.
- ♻️ **Live reloading for development**: Integrated live reload server to auto-update quizzes as you edit.
- 📐 **Mathematical equation support**: Native support for dollar-math (`$..$` and `$$..$$` ) based LaTeX-style equations for math-based quizzes.
- 💻 **Code block rendering**: Display code snippets within quiz questions for technical assessments.
- 💯 **Optional Scoring**: Optional scoring support.
- 🛠️ **Easy Integration**: Can be easily integrated into any system as it is available as a python package.
---

## 📝 Answer Types

Queck supports a variety of question types, including:

- **Choice Based**
  - The separater `/#` is used to mark option-wise feedback. To use the literal `/#`, use html code for / (&#47;) or # (&#35;) or both.
  - **Single Select Choices**\
    List of yaml string marked with `(o)` resembling resembling radio button.

    ```yaml
    answer:
      - ( ) Option 1
      - (o) Option 2 /# feedback for option 2
      - ( ) Option 3
      - ( ) Option 4
    ```

  - **Multiple Select Choices**\
    List of yaml string marked with `(x)` resembling to-do list or checkboxes.

    ```yaml
    answer:
      - ( ) Option 1
      - (x) Option 2 /# feedback for option 2
      - ( ) Option 3 /# feedback for option 3
      - (x) Option 4
    ```

  - **True/False**\
    Yaml value `true`/`false`.

    ```yaml
    answer: true
    ```

- **Numerical**
  - **Integer**\
    Yaml integer.

    ```yaml
    answer: 5
    ```

  - **Numerical Range**\
    Yaml string of format `{low}..{high}`.

    ```yaml
    answer: 1.25..1.35
    ```

  - **Numerical Tolerance**\
    Yaml string of format `{value}|{tolerance}`.

    ```yaml
    answer: 1.3|.5
    ```
  - **Single Floating Point Values**\
    By default floating point values are **not supported** as a best practice. But they can be added with range or tolerance type. For example, `0.5..0.5` or `0.5|0`.

- **Short Answer**\
  Yaml string.
  
  ```yaml
  answer: France
  ```

---

## Other validation rules
1. Every choice based question should have **atleast one incorrect option**. 
2. Common data questions should have **atleast two** contextual  questions inside them.

## VS Code Profile

The below VS code profile contains the necessary extensions and configurations for syntax highlighting and validation of queck files. 

https://gist.github.com/livinNector/596a7c507a95eaa59014df9505159ce8

Check [this](https://code.visualstudio.com/docs/configure/profiles#_import) for the instructions to import the vscode profile.

## 📄 Sample Queck Format

Refer the example queck files from [examples](/examples/).


---

## 🚀 Installation

### Installation as `uv tool`

The recommended way to install queck is to install as uv tool using the below command. Ensure [uv](https://docs.astral.sh/uv/getting-started/installation/) is installed your system.

```sh
uv tool install queck
```

### Installation using pip

Queck requres `python>=3.12` install the latest version of python before installing queck.

To install Queck, run the following command:

```sh
pip install queck
```

---

## 💻 Commands

### `qeuck format`

Formats the markdown content inside the queck file using mdformat.

```bash
queck format quiz.queck
```

### `queck export`

To export a quiz in HTML format with live watching enabled:

```bash
queck export path/to/quiz.queck --format html --output_folder export --render_mode fast --watch
```

- `--format`: Specify output format as `html`,`md` or `json`.
- `--output_folder`: Directory for exported files.
- `--render_mode`: (For html export only) Use `fast` for KaTeX and Highlight.js `compat` for inline styles, `latex` for using Latex.css.

Shorthands for options are also supported.

```bash
queck export path/to/quiz.queck -f html -o export -r fast -w
```

---

## Experimental GenAI Features

To enable this feature install queck using the following extras.

```bash
uv tool install "queck[genai]"
```

### `queck extract`

To extract questions from text based formats like markdown or latex.

```bash
queck extract path/to/file.md --model "openai:gpt-4o-mini"
```

The model is provided with the format `{provider}:{model_name}`

Available providers:
  - `openai`
  - `groq`



## 🤝 Contribution

We welcome contributions! Feel free to submit pull requests, report issues, or suggest new features. Let's make Queck better together! 🙌

---

## ⚖️ License

This project is licensed under the MIT License.