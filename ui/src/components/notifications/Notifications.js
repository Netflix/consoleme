import React, { useState } from "react";
import { Button, Modal, Dropdown, Grid, Message } from "semantic-ui-react";
import ReactMarkdown from "react-markdown";

export const NotificationsModal = (props) => {
  const [notifications, getNotifications] = useState([]);

  const closeNotifications = () => {
    props.closeNotifications();
  };

  // TODO: Link to role page, specifically, recent errors page
  // TODO: Make it possible to skip to self-service step 3 by providing role ARN and generated policy. Proper principal
  // format should be figured out by the backend
  // TODO: Mark notifications as read on backend. Maybe a lastReadTime ? Or mark them manually
  // TODO: When user clicks X, mark notification as deleted on the backend
  // TODO: Allow user to ignore errors for this role, this service, or this resource. Consider allowing them to ignore
  // all errors (Perhaps this can be a localstorage thing)
  // TODO: Consider adding review data here to. Your policy request was recently reviewed by X.
  // TODO: Only show 10 recent notifications rather than a huge list? Maybe notifications expire after 24 hours?
  // TODO: Other security notifications like IMDSv2?
  // TODO: Tell the user WHY they received the noitification. "You performed this action" vs "A role your team owns
  // performed this action
  // Notifications should have an expiration

  const notificationDisplay = (
    <>
      <Message>
        <ReactMarkdown
          linkTarget="_blank"
          source={
            "We generated a policy to resolve an error that you encountered on arn:blah. " +
            "Please click HERE to request the policy. Alternatively, click Here to see all generated policies for " +
            "this role. "
          }
        />
      </Message>
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
