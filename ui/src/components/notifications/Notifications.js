import React, { useEffect, useState } from "react";
import { Accordion, Button, Modal, Segment, Icon } from "semantic-ui-react";
import ReactMarkdown from "react-markdown";
import MonacoEditor from "react-monaco-editor";
import { getLocalStorageSettings } from "../../helpers/utils";
import { useAuth } from "../../auth/AuthProviderDefault";
import { useNotifications } from "../hooks/notifications";

export const NotificationsModal = (props) => {
  const { notifications, GetAndSetNotifications } = useNotifications();
  const { sendRequestCommon } = useAuth();
  const [activeTargets, setActiveTargets] = useState({});
  const editorTheme = getLocalStorageSettings("editorTheme");
  const closeNotifications = () => {
    props.closeNotifications();
  };
  const [notificationList, setNotificationList] = useState([]);
  //const [notifications, setNotifications] = useState(props.notifications)

  const toggleReadUnreadStatusForUser = (notification) => {
    const request = {
      action: "toggle_read_for_current_user",
      notifications: [notification],
    };
    sendRequestCommon(request, "/api/v2/notifications", "put");
  };
  const toggleHideFromUser = (notification) => {
    const request = {
      action: "toggle_hidden_for_current_user",
      notifications: [notification],
    };
    sendRequestCommon(request, "/api/v2/notifications", "put");
    // setNotifications( notifications.filter(item => item !== notification))
    GetAndSetNotifications();
  };

  const toggleHideFromAllUsers = (notification) => {
    const request = {
      action: "toggle_hidden_for_all_users",
      notifications: [notification],
    };
    sendRequestCommon(request, "/api/v2/notifications", "put");
  };

  const toggleMarkAllRead = (notifications) => {
    const request = {
      action: "toggle_read_for_current_user",
      notifications: notifications,
    };
    sendRequestCommon(request, "/api/v2/notifications", "put");
  };

  const toggleRequestForUser = (notification) => {
    console.log("here");
  };

  // TODO: Dynamically define buttons from backend
  // TODO: Make it possible to link specifically to recent errors page instead of primary role page
  // TODO: Error list on recent errors page should also allow generating request in as few clisk as possible
  // format should be figured out by the backend
  // TODO: When user clicks X, mark notification as deleted on the backend
  // TODO: Allow user to ignore errors for this role, this service, or this resource.

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
    console.log("rerender");
    setNotificationList(
      notifications.map(function (notification) {
        const { messageActions } = notification.message_actions.map(function (
          message_action
        ) {
          return (
            <Button
              icon="close"
              onClick={() => window.open(message_action.uri, "_blank")}
            >
              {message_action.text}
            </Button>
          );
        });
        return (
          <>
            <Segment color="blue">
              <Button.Group basic size="small" floated="right">
                <Button
                  icon="close"
                  onClick={() => {
                    toggleHideFromUser(notification);
                  }}
                />
              </Button.Group>
              <ReactMarkdown
                linkTarget="_blank"
                source={notification?.message}
              />
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
                  {/*TODO: Figure out why this doesn't expand until next refresh*/}
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
              <Button.Group>{messageActions}</Button.Group>
              {/*<Button.Group>*/}
              {/*  <Button*/}
              {/*    color={"green"}*/}
              {/*    onClick={() => {*/}
              {/*      toggleReadUnreadStatusForUser(notification);*/}
              {/*    }}*/}
              {/*  >*/}
              {/*    Mark as read*/}
              {/*  </Button>*/}
              {/*  <Button.Or />*/}
              {/*  <Button*/}
              {/*    color={"orange"}*/}
              {/*    onClick={() => {*/}
              {/*      toggleHideFromUser(notification);*/}
              {/*    }}*/}
              {/*  >*/}
              {/*    Hide from me*/}
              {/*  </Button>*/}
              {/*  <Button.Or />*/}
              {/*  <Button*/}
              {/*    color={"red"}*/}
              {/*    onClick={() => {*/}
              {/*      toggleHideFromAllUsers(notification);*/}
              {/*    }}*/}
              {/*  >*/}
              {/*    Hide from everyone*/}
              {/*  </Button>*/}
              {/*</Button.Group>*/}
            </Segment>
          </>
        );
      })
    );
  }, [notifications]);
  // let notificationList = notifications.map(function (notification) {
  //   return (
  //     <>
  //       <Segment color="blue">
  //         <Button.Group basic size="small" floated="right">
  //           <Button
  //             icon="close"
  //             onClick={() => {
  //               toggleHideFromUser(notification);
  //             }}
  //           />
  //         </Button.Group>
  //         <ReactMarkdown linkTarget="_blank" source={notification?.message} />
  //         <Accordion exclusive={false} fluid>
  //           <Accordion.Title
  //             active={activeTargets[notification?.predictable_id] === true}
  //             index={true}
  //             onClick={() => {
  //               let newState = activeTargets;
  //               newState[notification.predictable_id] = !newState[
  //                 notification.predictable_id
  //               ];
  //               setActiveTargets({
  //                 ...activeTargets,
  //                 ...newState,
  //               });
  //             }}
  //           >
  //             <Icon name="dropdown" />
  //             More Details
  //           </Accordion.Title>
  //           <Accordion.Content
  //             active={activeTargets[notification?.predictable_id] === true}
  //           >
  //             <MonacoEditor
  //               height="500"
  //               language="json"
  //               theme={editorTheme}
  //               value={JSON.stringify(notification?.details, null, 2)}
  //               options={monacoOptions}
  //               textAlign="center"
  //             />
  //           </Accordion.Content>
  //         </Accordion>
  //         <Button.Group>
  //           <Button
  //             color={"green"}
  //             onClick={() => {
  //               toggleRequestForUser(notification);
  //             }}
  //           ></Button>
  //         </Button.Group>
  //         {/*<Button.Group>*/}
  //         {/*  <Button*/}
  //         {/*    color={"green"}*/}
  //         {/*    onClick={() => {*/}
  //         {/*      toggleReadUnreadStatusForUser(notification);*/}
  //         {/*    }}*/}
  //         {/*  >*/}
  //         {/*    Mark as read*/}
  //         {/*  </Button>*/}
  //         {/*  <Button.Or />*/}
  //         {/*  <Button*/}
  //         {/*    color={"orange"}*/}
  //         {/*    onClick={() => {*/}
  //         {/*      toggleHideFromUser(notification);*/}
  //         {/*    }}*/}
  //         {/*  >*/}
  //         {/*    Hide from me*/}
  //         {/*  </Button>*/}
  //         {/*  <Button.Or />*/}
  //         {/*  <Button*/}
  //         {/*    color={"red"}*/}
  //         {/*    onClick={() => {*/}
  //         {/*      toggleHideFromAllUsers(notification);*/}
  //         {/*    }}*/}
  //         {/*  >*/}
  //         {/*    Hide from everyone*/}
  //         {/*  </Button>*/}
  //         {/*</Button.Group>*/}
  //       </Segment>
  //     </>
  //   );
  // });
  const notificationDisplay = (
    <>
      {/*{notificationList.length > 0 ? (*/}
      {/*  <Button*/}
      {/*    color={"green"}*/}
      {/*    onClick={() => {*/}
      {/*      toggleMarkAllRead(notifications);*/}
      {/*    }}*/}
      {/*  >*/}
      {/*    Mark all as read*/}
      {/*  </Button>*/}
      {/*) : null}*/}
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
