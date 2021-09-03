import React, { useEffect, useState } from "react";
import {
  Accordion,
  Button,
  Modal,
  Segment,
  Icon,
  Loader,
  Dimmer,
} from "semantic-ui-react";
import ReactMarkdown from "react-markdown";
import MonacoEditor from "react-monaco-editor";
import { getLocalStorageSettings } from "../../helpers/utils";
import { useAuth } from "../../auth/AuthProviderDefault";
import { useNotifications } from "../hooks/notifications";

export const NotificationsModal = (props) => {
  const { notifications, GetAndSetNotifications } = useNotifications();
  const { user, sendRequestCommon } = useAuth();
  const [activeTargets, setActiveTargets] = useState({});
  const editorTheme = getLocalStorageSettings("editorTheme");

  const closeNotifications = () => {
    markAllNotificationsAsReadForUser(notifications);
    props.closeNotifications();
  };

  const [notificationList, setNotificationList] = useState([]);
  const [loadingNotifications, setLoadingNotifications] = useState([]);

  const markAllNotificationsAsReadForUser = async (notifications) => {
    const request = {
      action: "toggle_read_for_current_user",
      notifications: [notifications],
    };

    await sendRequestCommon(request, "/api/v2/notifications", "put");
  };

  const toggleHideFromUser = async (notification) => {
    const request = {
      action: "toggle_hidden_for_current_user",
      notifications: [notification],
    };
    const predictable_id = notification.predictable_id;
    setLoadingNotifications([...loadingNotifications, predictable_id]);
    const res = await sendRequestCommon(
      request,
      "/api/v2/notifications",
      "put"
    );
    // setNotifications( notifications.filter(item => item !== notification))
    GetAndSetNotifications(user, res);
    setLoadingNotifications(
      loadingNotifications.filter((item) => item !== predictable_id)
    );
  };

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
  useEffect(() => {
    async function generateRenderedData() {
      setNotificationList(
        await Promise.all(
          notifications.map(async function (notification) {
            const messageActions = await Promise.all(
              notification.message_actions.map(async function (message_action) {
                return (
                  <Button
                    color="green"
                    onClick={() => window.open(message_action.uri, "_blank")}
                  >
                    {message_action.text}
                  </Button>
                );
              })
            );
            const predictable_id = notification?.predictable_id;
            return (
              <>
                <Segment color="blue">
                  <Dimmer
                    active={loadingNotifications.includes(predictable_id)}
                  >
                    <Loader>Submitting Request</Loader>
                  </Dimmer>
                  <Button.Group basic size="small" floated="right">
                    <Button
                      icon="close"
                      onClick={() => {
                        async function execute() {
                          await toggleHideFromUser(notification);
                        }

                        execute();
                      }}
                    />
                  </Button.Group>
                  <ReactMarkdown
                    linkTarget="_blank"
                    source={notification?.message}
                  />
                  <Accordion exclusive={false} fluid>
                    <Accordion.Title
                      active={
                        activeTargets[notification?.predictable_id] === true
                      }
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
                      active={
                        activeTargets[notification?.predictable_id] === true
                      }
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
                  <Button.Group>{messageActions}</Button.Group>
                </Segment>
              </>
            );
          })
        )
      );
    }
    generateRenderedData();
  }, [notifications, activeTargets, loadingNotifications]); // eslint-disable-line

  const notificationDisplay = (
    <>
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
