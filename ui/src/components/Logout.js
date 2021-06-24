import React, { useCallback, useEffect, useState } from "react";
import { useAuth } from "../auth/AuthProviderDefault";
import { Icon, Message } from "semantic-ui-react";

const Logout = () => {
  const { sendRequestCommon } = useAuth();
  const [errorMessage, setErrorMessage] = useState("");
  const onSignOut = useCallback(async () => {
    const signOutResponse = await sendRequestCommon(
      null,
      "/api/v2/logout",
      "get"
    );

    if (!signOutResponse) {
      return;
    }

    if (signOutResponse.redirect_url) {
      window.location.assign(signOutResponse.redirect_url);
    }

    setErrorMessage(signOutResponse.message);
  }, [sendRequestCommon]);

  useEffect(() => {
    (async () => {
      await onSignOut();
    })();
  }, [onSignOut]);
  return (
    <>
      {errorMessage ? (
        <Message negative>
          <Message.Header>Oops! there was a problem</Message.Header>
          <p>{errorMessage}</p>
        </Message>
      ) : (
        <Message icon>
          <Icon name="circle notched" loading />
          <Message.Content>
            <Message.Header>Just a moment...</Message.Header>
            Attempting to log out
          </Message.Content>
        </Message>
      )}
    </>
  );
};

export default Logout;
