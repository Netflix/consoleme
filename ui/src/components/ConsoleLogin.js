import React, { useState } from "react";
import { useParams, useLocation } from "react-router-dom";
import { Icon, Message } from "semantic-ui-react";
import { sendRequestCommon, setRecentRoles } from "../helpers/utils";

const signOutUrl = "https://signin.aws.amazon.com/oauth?Action=logout";

const ConsoleLogin = () => {
  const { search } = useLocation();
  const { roleQuery } = useParams();
  const [errorMessage, setErrorMessage] = useState("");

  const onSignIn = async () => {
    const roleData = await sendRequestCommon(
      null,
      "/api/v2/role_login/" + roleQuery + search,
      "get"
    );

    if (roleData.type === "redirect") {
      if (roleData.reason === "console_login") {
        setRecentRoles(roleData.role);
      }
      window.location.assign(roleData.redirect_url);
    }

    setErrorMessage(roleData.message);
  };

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
            <Message.Header>Just a few seconds...</Message.Header>
            Attempting to log into the AWS Console
          </Message.Content>
        </Message>
      )}
      <iframe
        onLoad={onSignIn}
        src={signOutUrl}
        style={{
          width: 0,
          height: 0,
          border: "none",
        }}
        title="Console Sign Out"
      />
    </>
  );
};

export default ConsoleLogin;
