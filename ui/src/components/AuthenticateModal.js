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
          Your authenticated session has expired. Please re-authenticate.
        </Modal.Description>
      </Modal.Content>
      <Modal.Actions>
        <Button content="Re-Authenticate" onClick={reloadPage} negative />
      </Modal.Actions>
    </Modal>
  );
};

export default AuthenticateModal;
