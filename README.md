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
- 🔍 **Schema validation with Pydantic**: Ensures your quiz structure is validated for correctness before exporting.
- 📤 **Flexible export options**: Export quizzes in **JSON**, **HTML** (print-ready), or **Markdown** formats.
- ⚙️ **Command-line interface**: Simple CLI for validation and export operations.
- ♻️ **Live reloading for development**: Integrated live reload server to auto-update quizzes as you edit.
- 📐 **Mathematical equation support**: Native support for dollar-math (`$..$` and `$$..$$` ) based LaTeX-style equations for math-based quizzes.
- 💻 **Code block rendering**: Display code snippets within quiz questions for technical assessments.
- 💯 **Optional Scoring**: Optional scoring support.

---

## 📝 Answer Types

Queck supports a variety of question types, including:

- **Choice Based**
  - **Single Select Choices**\
    list of yaml string marked with `(o)` resembling resembling radio button.

    ```yaml
    answer:
      - ( ) Option 1
      - (o) Option 2 // feedback for option 2
      - ( ) Option 3
      - ( ) Option 4
    ```

  - **Multiple Select Choices**\
    List of yaml string marked with `(x)` resembling to-do list or checkboxes.

    ```yaml
    answer:
      - ( ) Option 1
      - (x) Option 2 // feedback for option 2
      - ( ) Option 3
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

- **Short Answer**\
  Yaml string.
  
  ```yaml
  answer: France
  ```

---

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

```bash
queck format quiz.queck
```

### `queck export`

To export a quiz in HTML format with live watching enabled:

```bash
queck export path/to/quiz.queck --format html --output_folder export --render_mode fast --watch
```

- `--format`: Specify output format as `html` or `md`.
- `--output_folder`: Directory for exported files.
- `--render_mode`: Use `fast` for KaTeX and Highlight.js `compat` for inline styles, `latex` for using Latex.css.

---

## 🤝 Contribution

We welcome contributions! Feel free to submit pull requests, report issues, or suggest new features. Let's make Queck better together! 🙌

---

## ⚖️ License

This project is licensed under the MIT License.
