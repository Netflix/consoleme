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
    ).unsafe_ask()
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
    generated_config_dash_delimited = {}
    for question in template_config["questions"]:
        generated_config_dash_delimited = {
            k.replace(".", "-"): v for k, v in generated_config.items()
        }
        # if the question has a condition and it is not same, don't ask the question
        if "depends_on" in question:
            # If the the depended on key isn't present at all, then skip question
            if question["depends_on"] not in generated_config:
                continue
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
        if question.get("default") and isinstance(question["default"], str):
            try:
                default_ans = question.get("default", "").format(
                    **generated_config_dash_delimited
                )
            except KeyError:
                pass

        # Different prompts based on question type
        if question["type"] == "email":
            generated_config[question["config_variable"]] = questionary.text(
                message=question_text, validate=email_validator, default=default_ans
            ).unsafe_ask()
        elif question["type"] == "confirmation":
            generated_config[question["config_variable"]] = questionary.confirm(
                message=question_text, default=default_ans
            ).unsafe_ask()
        elif question["type"] == "text":
            if question.get("required", False):
                generated_config[question["config_variable"]] = questionary.text(
                    message=question_text,
                    default=default_ans,
                    validate=lambda text: True
                    if len(text) > 0
                    else "This is a required field",
                ).unsafe_ask()
            else:
                generated_config[question["config_variable"]] = questionary.text(
                    message=question_text,
                    default=default_ans,
                ).unsafe_ask()
        elif question["type"] == "select":
            choices = question["choices"]
            generated_config[question["config_variable"]] = questionary.select(
                choices=choices, message=question_text
            ).unsafe_ask()
        elif question["type"] == "list" or question["type"] == "list_dict":
            if question.get("required", False):
                values = questionary.text(
                    message=question_text,
                    default=default_ans,
                    validate=lambda text: True
                    if len(text) > 0
                    else "This is a required field",
                ).unsafe_ask()
            else:
                values = questionary.text(
                    message=question_text, default=default_ans
                ).unsafe_ask()
            if values != "":
                values = values.split(",")
                if question["type"] == "list":
                    generated_config[question["config_variable"]] = []
                    for val in values:
                        generated_config[question["config_variable"]].append(
                            val.strip()
                        )
                else:
                    generated_config[question["config_variable"]] = {}
                    for val in values:
                        val = val.strip()
                        val = val.split(":")
                        cur_key = question["config_variable"] + "." + val[0]
                        generated_config[cur_key] = val[1]
            else:
                generated_config[question["config_variable"]] = []
        # formatted keys
        if "format_text" in question:
            generated_config[question["config_variable"]] = question[
                "format_text"
            ].format(generated_config[question["config_variable"]])

    return generated_config


def update_nested_dict(d, k, v):
    if "." in k:
        cur_key = k.split(".")[0]
        leftover_key = k.split(".", 1)[1]
        d[cur_key] = update_nested_dict(d.get(cur_key, {}), leftover_key, v)
    else:
        d[k] = v
    return d


def generate_consoleme_style_config(generated_config):
    consoleme_generated_config = {}
    for k in generated_config:
        # skip those that are templated config variables and not actual config variables
        if k.startswith("__"):
            continue
        # skip non-values
        val = generated_config[k]
        if (isinstance(val, str) or isinstance(val, list)) and len(val) == 0:
            continue
        update_nested_dict(consoleme_generated_config, k, val)
    return consoleme_generated_config


def main():
    template_config = load_template_config()
    generated_config_path = (
        get_generated_config_path() + f"/generated_config_{int(time.time())}.yaml"
    )
    generated_config = ask_questions(template_config)
    consoleme_generated_config = generate_consoleme_style_config(generated_config)
    print(json.dumps(consoleme_generated_config, indent=4, sort_keys=True))
    print(f"Saving configuration to {generated_config_path}")
    try:
        with open(generated_config_path, "w") as file:
            yaml.dump(consoleme_generated_config, file)
        print(f"Configuration saved to {generated_config_path}")
    except Exception as e:
        print(f"An error occurred saving configuration file: {str(e)}")


if __name__ == "__main__":
    main()
