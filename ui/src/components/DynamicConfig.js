import React, { useState, useEffect } from "react";
import Editor from "@monaco-editor/react";
import {
  Header,
  Button,
  Icon,
  Grid,
  Segment,
  Message,
  Divider,
} from "semantic-ui-react";
import { useAuth } from "../auth/AuthProviderDefault";
import { getLocalStorageSettings } from "../helpers/utils";

function ConsoleMeDynamicConfig() {
  const [config, setConfig] = useState("");
  const [configSha256, setConfigSha256] = useState("");
  const [statusMessage, setStatusMessage] = useState(null);
  const { sendRequestCommon } = useAuth();
  const editorTheme = getLocalStorageSettings("editorTheme");

  useEffect(() => {
    async function fetchDynamicConfig() {
      const resJson = await sendRequestCommon(
        null,
        "/api/v2/dynamic_config",
        "get"
      );
      if (!resJson) {
        return;
      }
      setConfigSha256(resJson.sha256);
      setConfig(resJson.dynamicConfig);
    }
    fetchDynamicConfig();
  }, [sendRequestCommon]);

  const updateConfig = async () => {
    const res = await sendRequestCommon(
      { new_config: config, existing_sha256: configSha256 },
      "/api/v2/dynamic_config"
    );

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
      <Header as="h1">
        <Icon name="book" />
        Update Dynamic Configuration
      </Header>
      <Divider />
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
          <Editor
            height="100vh"
            defaultLanguage="yaml"
            theme={editorTheme}
            defaultValue={config}
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

export default ConsoleMeDynamicConfig;
