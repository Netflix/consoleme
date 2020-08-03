import React from 'react';
import { MonacoDiffEditor } from 'react-monaco-editor';
import PropTypes from 'prop-types';
import { getMonacoCompletions } from '../../helpers/utils';

monaco.languages.registerCompletionItemProvider('json', {
  async provideCompletionItems(model, position) {
    const response = await getMonacoCompletions(model, position);
    return response;
  },
});

class MonacoDiffComponent extends React.Component {
  constructor(props) {
    super(props);
    this.onLintError = props.onLintError;
    this.onValueChange = props.onValueChange;
    this.editorDidMount = this.editorDidMount.bind(this);
    this.onChange = this.onChange.bind(this);
    this.state = {
      modifiedEditor: null,
    };
  }

  onChange(newValue) {
    this.onValueChange(newValue);
  }

  editorDidMount(editor) {
    editor.modifiedEditor.onDidChangeModelDecorations(() => {
      const { modifiedEditor } = this.state;
      const model = modifiedEditor.getModel();
      if (model === null || model.getModeId() !== 'json') {
        return;
      }

      const owner = model.getModeId();
      const uri = model.uri;
      const markers = monaco.editor.getModelMarkers({ owner, resource: uri });
      this.onLintError(markers.map((marker) => `Lint error on line ${marker.startLineNumber} columns ${marker.startColumn}-${marker.endColumn}: ${marker.message}`));
    });
    this.setState({
      modifiedEditor: editor.modifiedEditor,
    });
  }

  render() {
    const { oldValue, newValue, readOnly } = this.props;
    const options = {
      selectOnLineNumbers: true,
      renderSideBySide: true,
      enableSplitViewResizing: false,
      quickSuggestions: true,
      readOnly,
    };
    return (
      <MonacoDiffEditor
        language="json"
        width="100%"
        height="500"
        original={oldValue}
        value={newValue}
        editorDidMount={this.editorDidMount}
        options={options}
        onChange={this.onChange}
        theme="vs-dark"
      />
    );
  }
}

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
