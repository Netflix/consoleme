import json
import os
import sys

import yaml

initial_options = {
    "clearInvisibleValues": "onHidden",
    "calculatedValues": []
}


def load_template_config():
    template_config_path = f"{os.path.dirname(__file__)}/template_config.yaml"
    try:
        with open(template_config_path, "r") as f:
            template_config = yaml.safe_load(f)
            return template_config
    except Exception as e:
        print(f"Error loading template config file: {str(e)}")
        sys.exit(1)


def generate_questions(template_config):
    generated_config = []
    for question in template_config["questions"]:
        cur_generated_question = {}
        # if the question has a condition
        if "depends_on" in question:
            cur_generated_question["visibleIf"] = "{" + f"{question['depends_on']}" + "}" + f" = '{question['depends_on_val'][0]}'"
            for idx in range(1, len(question["depends_on_val"])):
                value = question['depends_on_val'][idx]
                cur_generated_question["visibleIf"] += " or {" + f"{question['depends_on']}" + "}" + f" = '{value}'"

        # TODO: if it is not a question
        if question["type"] == "no_question":
            # generated_config[question["config_variable"]] = question["value"]
            continue

        # Generate the question text to ask
        question_text = template_config["default"][question["type"]].format(
            friendly_name=question["friendly_name"],
            friendly_description=question["friendly_description"],
        )
        cur_generated_question["title"] = question_text
        cur_generated_question["name"] = question["config_variable"]
        # if the question has a default answer
        # default_ans = question.get("default", "")
        if "default" in question:
            cur_generated_question["defaultValue"] = question["default"]
            # TODO: default formatting
            # if isinstance(question["default"], str) and "{" in question["default"]:
            #     variable = question["default"].split("{", 1)[1].split("}", 1)[0]
            #     value = variable if "-" not in variable else variable.replace("-", ".")
            #     initial_options["calculatedValues"].append(
            #         {
            #             "name": variable,
            #             "expression": value
            #         }
            #     )

        if question.get("required", False):
            cur_generated_question["isRequired"] = True

        # Different prompts based on question type
        if question["type"] == "email":
            cur_generated_question["type"] = "text"
            cur_generated_question["inputType"] = "email"
            cur_generated_question["autoComplete"] = "email"
            cur_generated_question["validators"] = [
                {
                    "type": "email"
                }
            ]
        elif question["type"] == "confirmation":
            cur_generated_question["type"] = "boolean"
        elif question["type"] == "text":
            cur_generated_question["type"] = "text"
        elif question["type"] == "select":
            cur_generated_question["type"] = "radiogroup"
            cur_generated_question["colCount"] = 1
            cur_generated_question["choices"] = question["choices"]
        elif question["type"] == "list" or question["type"] == "list_dict":
            cur_generated_question["type"] = "text"
            cur_generated_question["__extra_details"] = question["type"]
        generated_config.append(cur_generated_question)

    return generated_config


def main():
    template_config = load_template_config()
    generated_questions = generate_questions(template_config)
    generated_dict = {
        "questions": generated_questions,
        **initial_options
    }
    try:
        with open(f"{os.path.dirname(__file__)}/questions.js", "w") as file:
            file.write("const json = " + json.dumps(generated_dict, indent=4, sort_keys=True))
        print("Questions saved")
    except Exception as e:
        print(f"An error occurred saving questions file: {str(e)}")


if __name__ == "__main__":
    main()