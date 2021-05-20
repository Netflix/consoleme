import json
import os
import re
import sys
import time

import questionary
import yaml

# global variables
email_regex = r"^(\w|\.|\_|\-)+[@](\w|\_|\-|\.)+[.]\w{2,3}$"


def load_template_config():
    template_config_path = f"{os.path.dirname(__file__)}/template_config.yaml"
    try:
        with open(template_config_path, "r") as f:
            template_config = yaml.safe_load(f)
            return template_config
    except Exception as e:
        print(f"Error loading template config file: {str(e)}")
        sys.exit(1)


def get_generated_config_path():
    default_path = f"{os.path.dirname(__file__)}"
    generated_config_dir = questionary.path(
        message="Where do you want to save the generated config file?",
        default=default_path,
        only_directories=True,
    ).ask()
    if not os.path.isdir(generated_config_dir):
        print(f"Invalid path provided, saving to default path instead: {default_path}")
        return default_path
    return generated_config_dir


def email_validator(input_email: str):
    if re.search(email_regex, input_email):
        return True
    return "Invalid email: please enter a valid email address"


def ask_questions(template_config):
    generated_config = {}
    for question in template_config["questions"]:
        # if the question has a condition and it is not same, don't ask the question
        if "depends_on" in question:
            if (
                generated_config[question["depends_on"]]
                not in question["depends_on_val"]
            ):
                continue

        # if it is not a question
        if question["type"] == "no_question":
            generated_config[question["config_variable"]] = question["value"]
            continue

        # Generate the question text to ask
        question_text = template_config["default"][question["type"]].format(
            friendly_name=question["friendly_name"],
            friendly_description=question["friendly_description"],
        )
        # if the question has a default answer
        default_ans = question.get("default", "")

        # Different prompts based on question type
        if question["type"] == "email":
            generated_config[question["config_variable"]] = questionary.text(
                message=question_text, validate=email_validator, default=default_ans
            ).ask()
        elif question["type"] == "confirmation":
            generated_config[question["config_variable"]] = questionary.confirm(
                message=question_text, default=default_ans
            ).ask()
        elif question["type"] == "text":
            generated_config[question["config_variable"]] = questionary.text(
                message=question_text,
                default=default_ans,
            ).ask()
        elif question["type"] == "select":
            choices = question["choices"]
            generated_config[question["config_variable"]] = questionary.select(
                choices=choices, message=question_text
            ).ask()
        elif question["type"] == "list":
            generated_config[question["config_variable"]] = questionary.text(
                message=question_text, default=default_ans
            ).ask()
            generated_config[question["config_variable"]] = (
                generated_config[question["config_variable"]]
            ).split(",")

        # formatted keys
        if "format_text" in question:
            generated_config[question["config_variable"]] = question[
                "format_text"
            ].format(generated_config[question["config_variable"]])

    return generated_config


def main():
    template_config = load_template_config()
    generated_config_path = (
        get_generated_config_path() + f"/generated_config_{int(time.time())}.yaml"
    )
    generated_config = ask_questions(template_config)
    print(json.dumps(generated_config, indent=4, sort_keys=True))
    # Below line because pre-commit complains about unused variable.....
    print(f"TODO: Save generated config to YAML {generated_config_path}")


if __name__ == "__main__":
    main()
