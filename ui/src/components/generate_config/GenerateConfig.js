import React, { useState } from "react";
import * as Survey from "survey-react";
import "survey-react/survey.css";
import { questions_json } from "./questions.js";
import Editor from "@monaco-editor/react";
import yaml from "js-yaml";
import { Header, Icon, Message, Popup, Segment } from "semantic-ui-react";
import "./GenerateConfig.css";
import { getLocalStorageSettings } from "../../helpers/utils";

const generated_config_editor_options = {
  selectOnLineNumbers: true,
  readOnly: true,
  scrollbar: {
    alwaysConsumeMouseWheel: false,
  },
  scrollBeyondLastLine: false,
  automaticLayout: true,
};

function GenerateConfig() {
  const [complete, setComplete] = useState(false);
  const [results, setResults] = useState({});
  const [messages, setMessages] = useState([]);
  const editorTheme = getLocalStorageSettings("editorTheme");
  const getSpecialTypes = (questions) => {
    const specialTypes = {};
    const formatTypes = {};
    for (let i = 0; i < questions.length; i++) {
      if (questions[i].hasOwnProperty("__extra_details")) {
        specialTypes[questions[i].name] = questions[i].__extra_details;
      }
      if (questions[i].hasOwnProperty("__format_text")) {
        formatTypes[questions[i].name] = questions[i].__format_text;
      }
    }
    return [specialTypes, formatTypes];
  };
  const clearMessage = async () => {
    const timer = setTimeout(() => {
      setMessages([]);
    }, 3000);
    return () => clearTimeout(timer);
  };
  const onComplete = (results) => {
    setComplete(true);
    let resultsConsoleMeStyle = {};
    const [specialTypes, formatTypes] = getSpecialTypes(
      questions_json.questions
    );
    for (let [key, value] of Object.entries(results.data)) {
      if (!key.startsWith("__")) {
        const updatedKey = key.split("_PLACEHOLDER_")[0];
        if (
          typeof value === "string" &&
          value.includes("{") &&
          value.includes("}")
        ) {
          let replacement = value.substring(
            value.lastIndexOf("{") + 1,
            value.lastIndexOf("}")
          );
          replacement = replacement.replaceAll("-", ".");
          if (results.data.hasOwnProperty(replacement)) {
            value = value.replace(
              "{" + replacement + "}",
              results.data[replacement]
            );
          }
        }
        if (formatTypes.hasOwnProperty(key)) {
          value = formatTypes[key].replace("{}", value);
        }
        if (specialTypes.hasOwnProperty(key) && specialTypes[key] === "list") {
          const updatedValue = value.split(",");
          updatedValue.forEach(function (part, index) {
            this[index] = this[index].trim();
          }, updatedValue);
          updateNestedObj(resultsConsoleMeStyle, updatedKey, updatedValue);
        } else if (
          specialTypes.hasOwnProperty(key) &&
          specialTypes[key] === "list_dict"
        ) {
          const updatedValue = value.split(",");
          const updatedValueDict = {};
          updatedValue.forEach((val) => {
            const splits = val.split(":");
            updatedValueDict[splits[0].trim()] = splits[1].trim();
          });
          updateNestedObj(resultsConsoleMeStyle, updatedKey, updatedValueDict);
        } else {
          updateNestedObj(resultsConsoleMeStyle, updatedKey, value);
        }
      }
    }
    setResults(resultsConsoleMeStyle);
  };
  const updateNestedObj = (d, k, v) => {
    if (k.includes(".")) {
      const dotIndex = k.indexOf(".");
      const splits = [k.slice(0, dotIndex), k.slice(dotIndex + 1)];
      const nextObj = d.hasOwnProperty(splits[0]) ? d[splits[0]] : {};
      d[splits[0]] = updateNestedObj(nextObj, splits[1], v);
    } else {
      d[k] = v;
    }
    return d;
  };
  const copyToClipboard = () => {
    navigator.clipboard.writeText(yaml.dump(results, 4)).then((r) => {
      setMessages(["Copied to Clipboard!"]);
      clearMessage();
    });
  };
  const downloadConfig = () => {
    const fileName = `consoleme_generated_config_${new Date().getTime()}.yaml`;
    const data = yaml.dump(results, 4);
    const blob = new Blob([data], { type: "yaml" });
    const href = URL.createObjectURL(blob);
    const link = document.createElement("a");
    link.href = href;
    link.download = fileName;
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
    setMessages([]);
  };
  const messagesToShow = () => {
    return messages.length > 0 ? (
      <Segment>
        <Message positive>
          <Message.Header>Success!</Message.Header>
          <Message.List>
            {messages.map((message) => (
              <Message.Item>{message}</Message.Item>
            ))}
          </Message.List>
        </Message>
      </Segment>
    ) : null;
  };
  const headerContent = () => {
    return (
      <Segment>
        <Header>
          Your ConsoleMe configuration has been generated! You can either copy
          it to clipboard, or download it as a file by clicking below.
        </Header>
        <Popup
          content="Copy to Clipboard"
          trigger={
            <Icon link name="copy" size="big" onClick={copyToClipboard} />
          }
        />
        <Popup
          content="Download Configuration"
          trigger={
            <Icon link name="download" size="big" onClick={downloadConfig} />
          }
        />
      </Segment>
    );
  };
  const customCSS = (survey, options) => {
    let classes = options.cssClasses;

    if (options.question.isRequired) {
      classes.title += " sq-title-required";
    }
    // Hide questions that are internally set (read only questions)
    if (options.question.readOnly) {
      classes.mainRoot += " sq-hidden-custom";
    }
    // Hide question number, because we hide questions, numbers become wonky
    classes.number += " sq-hidden-custom";
  };

  const surveyContent = () => {
    if (!complete) {
      return (
        <Survey.Survey
          json={questions_json}
          showCompletedPage={true}
          onComplete={onComplete}
          onUpdateQuestionCssClasses={customCSS}
        />
      );
    }
    return (
      <Segment.Group>
        {headerContent()}
        {messagesToShow()}
        <Editor
          height="700px"
          defaultLanguage="yaml"
          width="100%"
          theme={editorTheme}
          value={yaml.dump(results, 4)}
          options={generated_config_editor_options}
          textAlign="center"
        />
      </Segment.Group>
    );
  };

  return <div>{surveyContent()}</div>;
}

export default GenerateConfig;
