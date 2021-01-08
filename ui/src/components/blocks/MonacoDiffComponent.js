import React, { useState, useEffect } from "react";
import { MonacoDiffEditor } from "react-monaco-editor";
import PropTypes from "prop-types";
import {
  getMonacoCompletions,
  getMonacoTriggerCharacters,
} from "../../helpers/utils";
import * as monaco from "monaco-editor/esm/vs/editor/editor.api.js";

monaco.languages.registerCompletionItemProvider("json", {
  triggerCharacters: getMonacoTriggerCharacters(),
  async provideCompletionItems(model, position) {
    const response = await getMonacoCompletions(model, position, monaco);
    return response;
  },
});
const MonacoDiffComponent = (props) => {
  const onLintError = props.onLintError;
  const onValueChange = props.onValueChange;
  // this.editorDidMount = this.editorDidMount.bind(this);
  // this.onChange = this.onChange.bind(this);
  let timer = null;

  const [debounceWait, setDebounceWait] = useState(300);
  const [modifiedEditor, setModifiedEditor] = useState(null);
  const [triggerCharacters, setTriggerCharacters] = useState(
    getMonacoTriggerCharacters()
  );

  const onChange = (newValue, e) => {
    onValueChange(newValue);
  };

  const editorDidMount = (editor) => {
    editor.modifiedEditor.onDidChangeModelDecorations(() => {
      const model = modifiedEditor.getModel();
      if (model === null || model.getModeId() !== "json") {
        return;
      }

      const owner = model.getModeId();
      const uri = model.uri;
      const markers = monaco.editor.getModelMarkers({ owner, resource: uri });
      onLintError(
        markers.map(
          (marker) =>
            `Lint error on line ${marker.startLineNumber} columns ${marker.startColumn}-${marker.endColumn}: ${marker.message}`
        )
      );
    });
    setModifiedEditor(editor.modifiedEditor);
  };

  const { oldValue, newValue, readOnly } = props;
  const options = {
    selectOnLineNumbers: true,
    renderSideBySide: true,
    enableSplitViewResizing: false,
    quickSuggestions: true,
    scrollbar: {
      alwaysConsumeMouseWheel: false,
    },
    scrollBeyondLastLine: false,
    automaticLayout: true,
    readOnly,
  };
  return (
    <MonacoDiffEditor
      language="json"
      width="100%"
      height="500"
      original={oldValue}
      value={newValue}
      editorWillMount={this.editorWillMount}
      editorDidMount={this.editorDidMount}
      options={options}
      onChange={(e) => onChange(e)}
      theme="vs-dark"
      alwaysConsumeMouseWheel={false}
    />
  );
};

// This component requires four props:
// 1. oldValue = old value for the diff
// 2. newValue = new value for the diff
// 3. readOnly = whether the new value should be readOnly or not
// 4. onLintError = method that will be called whenever a lint error is detected
// 5. onChange = method that will be called whenever a chance occurs to upate the value

MonacoDiffComponent.propTypes = {
  oldValue: PropTypes.string.isRequired,
  newValue: PropTypes.string.isRequired,
  readOnly: PropTypes.bool.isRequired,
  onLintError: PropTypes.func.isRequired,
  onValueChange: PropTypes.func.isRequired,
};

export default MonacoDiffComponent;
