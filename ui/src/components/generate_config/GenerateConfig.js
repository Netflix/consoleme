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
  const onComplete = (results) => {
    setComplete(true);
    // TODO some manipulation for certain keys (lists, list of dicts)
    let resultsConsoleMeStyle = {};
    for (const [key, value] of Object.entries(results.data)) {
      if (!key.startsWith("__")) {
        updateNestedObj(resultsConsoleMeStyle, key, value);
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
