import React, { useState } from "react";
import * as Survey from "survey-react";
import "survey-react/survey.css";
import { questions_json } from "./questions.js";
import MonacoEditor from "react-monaco-editor";

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
    // TODO actual generation of config based on results here
    setResults(results.data);
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
    // Placeholder for now, the results need to be converted to YAML that ConsoleMe configs are in
    return (
      <MonacoEditor
        height="500px"
        language="json"
        width="100%"
        theme="vs-dark"
        value={JSON.stringify(results, null, 4)}
        options={generated_config_editor_options}
        textAlign="center"
      />
    );
  };

  return <div>{surveyContent()}</div>;
}

export default GenerateConfig;
