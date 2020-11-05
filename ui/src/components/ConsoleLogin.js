import React, { ComponentType, useState } from "react";
import { sendRequestCommon } from "../helpers/utils";
import { useParams } from "react-router-dom";
import qs from "qs";
import { Message } from "semantic-ui-react";

function ConsoleLogin(props) {
  const { roleQuery } = useParams();
  const [queryString, setQueryString] = useState(window.location.search);
  const [signOut, setSignOut] = useState(false);
  const [errorMessage, setErrorMessage] = useState("");
  const signOutUrl = "https://signin.aws.amazon.com/oauth?Action=logout";
  const logOutIframeStyle = {
    width: 0,
    height: 0,
    border: "none",
  };
  console.log(queryString);
  console.log(roleQuery);
  // Parse query string
  // POST to backend
  // If told to redirect due to successful authz, trigger logout iframe
  // If told to redirect to main page due to error or multiple roles, handle the redirect, filter,  and display message
  // POST to http://localhost:3000/api/v2/role_login/roledetails

  // const roleData = await sendRequestCommon(
  //   {
  //     limit: 1000,
  //   },
  //   "/"
  // );
  const loginAndRedirect = async () => {
    const roleData = await sendRequestCommon(
      null,
      "/api/v2/role_login/" + roleQuery + queryString,
      "get"
    );

    if (roleData.type === "redirect" && roleData.reason === "error") {
      window.location.href = roleData.redirect_url;
    }

    if (roleData.type === "redirect" && roleData.reason === "console_login") {
      // Success
      // TODO: Set Recent Roles
      // TODO: Test iframe
      // TODO: Delay redirect
      setSignOut(true);
      setTimeout(() => {
        window.location.href = roleData.redirect_url;
      }, 2000);

      return;
    }

    if (roleData.type === "error") {
      setErrorMessage(roleData.message);
    }

    console.log(roleData);
    const parsedQueryString = qs.parse(queryString, {
      ignoreQueryPrefix: true,
    });

    console.log(parsedQueryString);
  };
  // "https://signin.aws.amazon.com/oauth?Action=logout"

  const result = loginAndRedirect();

  return (
    <>
      {errorMessage ? (
        <Message negative>
          <Message.Header>Oops! there was a problem</Message.Header>
          <p>{errorMessage}</p>
        </Message>
      ) : null}
      <p>Attempting to log into the AWS Console.</p>
      <p>Please wait a second.</p>
      <iframe
        className="logOutIframe"
        style={logOutIframeStyle}
        src={signOut ? signOutUrl : null}
      />
    </>
  );
}

export default ConsoleLogin;
