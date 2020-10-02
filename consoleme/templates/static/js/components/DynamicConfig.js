import React, { useState, useEffect } from "react";
import { render } from "react-dom";
import MonacoEditor from "react-monaco-editor";
import {
  Header,
  Button,
  Icon,
  Grid,
  Segment,
  Message,
} from "semantic-ui-react";
import { sendRequestCommon } from "../helpers/utils";

function DynamicConfig() {
  const [config, setConfig] = useState("");
  const [configSha256, setConfigSha256] = useState("");
  const [statusMessage, setStatusMessage] = useState(null);

  useEffect(() => {
    async function fetchDynamicConfig() {
      const res = await fetch("/api/v2/dynamic_config");
      const resJson = await res.json();
      setConfigSha256(resJson.sha256);
      setConfig(resJson.dynamicConfig);
    }
    fetchDynamicConfig();
  }, []);

  const updateConfig = async () => {
    const res = await sendRequestCommon(
      { new_config: config, existing_sha256: configSha256 },
      "/api/v2/dynamic_config"
    );
    console.log(res);
    if (res.status === "success") {
      setStatusMessage(
        <Message positive>
          <Message.Header>Success</Message.Header>
          <Message.Content>
            Successfully updated Dynamic Configuration
          </Message.Content>
        </Message>
      );
      setConfigSha256(res.newsha56);
      setConfig(res.newConfig);
    }
    if (res.status === "error") {
      setStatusMessage(
        <Message negative>
          <Message.Header>Oops! There was a problem.</Message.Header>
          <Message.Content>{res.error}</Message.Content>
        </Message>
      );
    }
  };

  const header = (
    <div>
      <Header as="h2" icon textAlign="center">
        <Icon name="book" circular />
        Update Dynamic Configuration
      </Header>
    </div>
  );

  const onChange = (newValue) => {
    setConfig(newValue);
  };

  const options = {
    selectOnLineNumbers: true,
    quickSuggestions: true,
    scrollbar: {
      alwaysConsumeMouseWheel: false,
    },
    scrollBeyondLastLine: false,
    automaticLayout: true,
  };

  return (
    <div>
      {header}
      <Grid centered columns={1}>
        <Grid.Column>
          <MonacoEditor
            height="1000"
            language="yaml"
            theme="vs-dark"
            value={config}
            onChange={onChange}
            options={options}
            textAlign="center"
          />
        </Grid.Column>
      </Grid>
      {statusMessage}
      <Segment basic textAlign="center">
        <Button primary type="submit" onClick={updateConfig}>
          Save Dynamic Configuration
        </Button>
      </Segment>
    </div>
  );
}

render(<DynamicConfig />, document.getElementById("dynamic_config"));
