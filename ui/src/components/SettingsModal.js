import React, { useState } from "react";
import { Button, Modal, Dropdown, Grid, Message } from "semantic-ui-react";
import {
  editor_themes,
  getLocalStorageSettings,
  setLocalStorageSettings,
} from "../helpers/utils";

const SettingsModal = (props) => {
  const [currentSettings, setCurrentSettings] = useState(
    JSON.parse(JSON.stringify(getLocalStorageSettings()))
  );
  const [messages, setMessages] = useState([]);

  const saveSettings = () => {
    setLocalStorageSettings(currentSettings);
    setMessages(["Settings have been successfully updated!"]);
  };
  const closeSettings = () => {
    setCurrentSettings(JSON.parse(JSON.stringify(getLocalStorageSettings())));
    setMessages([]);
    props.closeSettings();
  };

  const updateEditorTheme = (e, data) => {
    const oldSettings = currentSettings;
    oldSettings.editorTheme = data.value;
    setMessages([]);
    setCurrentSettings(oldSettings);
  };

  const editorThemeSettings = () => {
    return (
      <Grid verticalAlign="middle">
        <Grid.Row>
          <Grid.Column width={4} floated="left">
            Editor Theme
          </Grid.Column>
          <Grid.Column width={8}>
            <Dropdown
              fluid
              placeholder="Select Theme"
              selection
              onChange={updateEditorTheme}
              defaultValue={currentSettings.editorTheme}
              options={editor_themes}
            />
          </Grid.Column>
        </Grid.Row>
      </Grid>
    );
  };
  const getMessages = () => {
    if (messages.length > 0) {
      return (
        <Message positive>
          <Message.Header>Success</Message.Header>
          <Message.Content>{messages[0]}</Message.Content>
        </Message>
      );
    }
    return null;
  };

  return (
    <Modal open={props.isOpen} onClose={closeSettings}>
      <Modal.Header>Settings</Modal.Header>
      <Modal.Content>
        <Modal.Description>{editorThemeSettings()}</Modal.Description>
        {getMessages()}
      </Modal.Content>
      <Modal.Actions>
        <Button
          content="Save Settings"
          labelPosition="left"
          icon="arrow right"
          onClick={saveSettings}
          positive
        />
        <Button
          content="Cancel"
          onClick={closeSettings}
          icon="cancel"
          negative
        />
      </Modal.Actions>
    </Modal>
  );
};

export default SettingsModal;
