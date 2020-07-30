import React from 'react';
import MonacoDiffEditor from 'react-monaco-editor';

class InlinePolicyChangeComponentMonaco extends React.Component {
  constructor(props) {
    super(props);
    const old_policy_doc = this.props.change.old_policy && this.props.change.old_policy.policy_document || {};
    const allOldKeys = [];
    JSON.stringify(old_policy_doc, (key, value) => { allOldKeys.push(key); return value; });
    const new_policy_doc = this.props.change.policy.policy_document && this.props.change.policy.policy_document || {};
    const allnewKeys = [];
    JSON.stringify(new_policy_doc, (key, value) => { allnewKeys.push(key); return value; });
    this.state = {
      old_policy: JSON.stringify(old_policy_doc, allnewKeys.sort(), 4),
      new_policy: JSON.stringify(new_policy_doc, allnewKeys.sort(), 4),
    };
  }

  editorDidMount(editor, monaco) {
    console.log('editorDidMount', editor);
    editor.focus();
  }

  onChange(newValue, e) {
    console.log('onChange', newValue, e);
  }

  render() {
    const options = {
      selectOnLineNumbers: true,
      renderSideBySide: true,
      enableSplitViewResizing: false,
    };
    return (
      <MonacoDiffEditor
        language="json"
        width="800"
        height="600"
        original={'abcdefg\nafsdfasdf'}
        value={'abcdefg\nafsdfasdf123'}
        options={options}
        theme="vs-dark"
      />
    );
  }
}

export default InlinePolicyChangeComponentMonaco;
