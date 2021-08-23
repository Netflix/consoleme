import React, { useState } from "react";
import { Accordion, Button, Modal, Segment, Icon } from "semantic-ui-react";
import ReactMarkdown from "react-markdown";
import MonacoEditor from "react-monaco-editor";
import { getLocalStorageSettings } from "../../helpers/utils";

export const NotificationsModal = (props) => {
  const [activeTargets, setActiveTargets] = useState({});
  const editorTheme = getLocalStorageSettings("editorTheme");
  const closeNotifications = () => {
    props.closeNotifications();
  };

  // TODO: Link to role page, specifically, recent errors page
  // format should be figured out by the backend
  // TODO: When user clicks X, mark notification as deleted on the backend
  // TODO: Allow user to ignore errors for this role, this service, or this resource. Consider allowing them to ignore
  // TODO: Only show 10 recent notifications rather than a huge list? Maybe notifications expire after 24 hours?

  const monacoOptions = {
    selectOnLineNumbers: true,
    quickSuggestions: true,
    scrollbar: {
      alwaysConsumeMouseWheel: false,
    },
    scrollBeyondLastLine: false,
    automaticLayout: true,
    wordWrap: true,
    readOnly: true,
  };
  let notificationList = props.notifications.map(function (notification) {
    return (
      <>
        <Segment>
          <ReactMarkdown linkTarget="_blank" source={notification?.message} />
          <Accordion exclusive={false} fluid>
            <Accordion.Title
              active={activeTargets[notification?.predictable_id] === true}
              index={true}
              onClick={() => {
                let newState = activeTargets;
                newState[notification.predictable_id] = !newState[
                  notification.predictable_id
                ];
                setActiveTargets({
                  ...activeTargets,
                  ...newState,
                });
              }}
            >
              <Icon name="dropdown" />
              More Details
            </Accordion.Title>
            <Accordion.Content
              active={activeTargets[notification?.predictable_id] === true}
            >
              <MonacoEditor
                height="500"
                language="json"
                theme={editorTheme}
                value={JSON.stringify(notification?.details, null, 2)}
                options={monacoOptions}
                textAlign="center"
              />
            </Accordion.Content>
          </Accordion>
          <Button.Group>
            <Button color={"green"}>Mark as read</Button>
            <Button.Or />
            <Button color={"orange"}>Hide from me</Button>
            <Button.Or />
            <Button color={"red"}>Hide from everyone</Button>
          </Button.Group>
        </Segment>
      </>
    );
  });
  const notificationDisplay = (
    <>
      {notificationList.length > 0 ? (
        <Button color={"green"}>Mark all as read</Button>
      ) : null}
      {notificationList.length > 0 ? (
        notificationList
      ) : (
        <p>You do not have any notifications.</p>
      )}
    </>
  );

  return (
    <Modal open={props.isOpen} onClose={closeNotifications}>
      <Modal.Header>Notifications</Modal.Header>
      <Modal.Content>{notificationDisplay}</Modal.Content>
      <Modal.Actions>
        <Button content="Close" onClick={closeNotifications} icon="cancel" />
      </Modal.Actions>
    </Modal>
  );
};
