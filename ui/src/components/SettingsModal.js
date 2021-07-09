import React, { useState } from "react";
import { Button, Modal, Dropdown, Grid } from "semantic-ui-react";
import { editor_themes, getLocalStorageSettings } from "../helpers/utils";

const SettingsModal = (props) => {
  const [currentSettings, setCurrentSettings] = useState(
    JSON.parse(JSON.stringify(getLocalStorageSettings()))
  );

  const saveSettings = () => {
    console.log("Save");
  };
  const closeSettings = () => {
    setCurrentSettings(JSON.parse(JSON.stringify(getLocalStorageSettings())));
    props.closeSettings();
  };

  const updateEditorTheme = (e, data) => {
    const oldSettings = currentSettings;
    oldSettings.editorTheme = data.value;
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

  return (
    <Modal open={props.isOpen}>
      <Modal.Header>Settings</Modal.Header>
      <Modal.Content>
        <Modal.Description>{editorThemeSettings()}</Modal.Description>
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
