# 🌟 Queck: An YAML based Format for Quiz Authoring

**Queck** is a simple and structured format for authoring quizzes based on **YAML** and **Markdown**. It provides a flexible schema for different types of questions, supporting both basic and complex quiz designs. Queck can export quizzes into **HTML** or **Markdown**, with options for live watching and automatic re-exporting upon file changes.

---

## 🆚 Alternatives

- **GIFT** – A widely used Moodle format for quiz authoring, but with more complex syntax compared to Queck’s simple YAML structure.

---

## 🔑 Key Features

- 📝 **YAML-based quiz authoring**: Author quizzes in a clean, human-readable YAML format.
- 🧠 **Support for diverse question types**: Including multiple-choice, true/false, numerical answers, comprehension passages, and more.
- ✔️ **Multiple answer formats**: Single correct answers, multiple select, numerical ranges, and tolerance-based answers.
- 🔍 **Schema validation with Pydantic**: Ensures your quiz structure is validated for correctness before exporting.
- 📤 **Flexible export options**: Export quizzes in **JSON**, **HTML** (print-ready), or **Markdown** formats.
- ⚙️ **Command-line interface**: Simple CLI for validation and export operations.
- ♻️ **Live reloading for development**: Integrated live reload server to auto-update quizzes as you edit.
- 📐 **Mathematical equation support**: Native support for LaTeX-style equations for math-based quizzes.
- 💻 **Code block rendering**: Display code snippets within quiz questions for technical assessments.
- 💯 **Optional Scoring**: Optional scoring support.
---

## 📝 Question Types

Queck supports a variety of question types, including:

- **Multiple Choice Questions (MCQ)**
- **Multiple Select Questions (MSQ)**
- **Numerical Answer Type (NAT)**
- **True/False**
- **Short Answer (SA)**
- **Comprehension or Common Data Questions** – With multiple sub-questions based on a shared passage.

---

## ✏️ Answer formats
- Choices
  ```yaml
  - ( ) Option 1
  - (x) Option 2 // feedback for option 2
  - ( ) Option 3
  - ( ) Option 4
  ```
- Numerical
  - Integer match  - `42`
  - Range match - `1.15..1.17`
  - Tolerance match - `1.16|0.01`
- Text (Short Answer) - `apple`
- True/False - `true` or `false`
---

## 📄 Sample Queck Format

Refer the example queck files from [examples](/examples/).


---

## 🚀 Installation

To install Queck, run the following command:

```sh
pip install "git+https://github.com/livinNector/queck.git"
```

---

## 💻 Example Command

To export a quiz in HTML format with live watching enabled:

```bash
queck export path/to/quiz.yaml --format html --output_folder export --render_mode fast --watch
```

- `--format`: Specify output format as `html` or `md`.
- `--output_folder`: Directory for exported files.
- `--render_mode`: Use `fast` for KaTeX and Highlight.js, or `compat` for MathJax and Pygments.

---

## 🤝 Contribution

We welcome contributions! Feel free to submit pull requests, report issues, or suggest new features. Let's make Queck better together! 🙌

---

## ⚖️ License

This project is licensed under the MIT License.
