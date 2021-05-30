// import React, { useState, useEffect } from "react";
// import MonacoEditor from "react-monaco-editor";
// import {
//   Header,
//   Button,
//   Icon,
//   Grid,
//   Segment,
//   Message,
//   Divider,
// } from "semantic-ui-react";
// import { useAuth } from "../../auth/AuthProviderDefault";
import React from "react";
import * as Survey from "survey-react";
import "survey-react/survey.css";
import { questions_json } from "./questions.js";

function GenerateConfig() {
  const onComplete = (results) => {
    console.log(results.data);
    // TODO actual generation of config based on results
  };
  return (
    <div>
      <Survey.Survey
        json={questions_json}
        showCompletedPage={true}
        onComplete={onComplete}
      />
    </div>
  );
}

export default GenerateConfig;
