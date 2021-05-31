import React, { useState } from "react";
import * as Survey from "survey-react";
import "survey-react/survey.css";
import { questions_json } from "./questions.js";
import MonacoEditor from "react-monaco-editor";
import yaml from "js-yaml";

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
  const getSpecialTypes = (questions) => {
    const specialTypes = {};
    for (let i = 0; i < questions.length; i++) {
      if (questions[i].hasOwnProperty("__extra_details")) {
        specialTypes[questions[i].name] = questions[i].__extra_details;
      }
    }
    return specialTypes;
  };
  const onComplete = (results) => {
    setComplete(true);
    let resultsConsoleMeStyle = {};
    const specialTypes = getSpecialTypes(questions_json.questions);
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
  const surveyContent = () => {
    if (!complete) {
      return (
        <Survey.Survey
          json={questions_json}
          showCompletedPage={true}
          onComplete={onComplete}
        />
      );
    }
    // TODO: show copy/save to file button
    return (
      <MonacoEditor
        height="700px"
        language="yaml"
        width="100%"
        theme="vs-dark"
        value={yaml.dump(results, 4)}
        options={generated_config_editor_options}
        textAlign="center"
      />
    );
  };

  return <div>{surveyContent()}</div>;
}

export default GenerateConfig;
