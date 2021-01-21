import React from "react";
import { Button, Modal } from "semantic-ui-react";
import { useAuth } from "../auth/AuthProviderDefault";

const AuthenticateModal = () => {
  const { isSessionExpired, setIsSessionExpired } = useAuth();

  const reloadPage = () => {
    window.location.reload(true);
  };

  return (
    <Modal
      onClose={() => setIsSessionExpired(false)}
      onOpen={() => setIsSessionExpired(true)}
      open={isSessionExpired}
      closeOnDimmerClick={false}
    >
      <Modal.Header>Session Expired</Modal.Header>
      <Modal.Content>
        <Modal.Description>
          You have been logged out. Please press the button to refresh you log
          back.
        </Modal.Description>
      </Modal.Content>
      <Modal.Actions>
        <Button
          content="Refresh and log me back in"
          onClick={reloadPage}
          negative
        />
      </Modal.Actions>
    </Modal>
  );
};

export default AuthenticateModal;
