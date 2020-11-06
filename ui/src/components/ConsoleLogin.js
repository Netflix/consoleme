import React, { useState } from "react";
import { useParams } from "react-router-dom";
import { Message } from "semantic-ui-react";
import { sendRequestCommon, parseLocalStorageCache } from "../helpers/utils";

function ConsoleLogin() {
  const { roleQuery } = useParams();
  const queryString = window.location.search;
  const [signOut, setSignOut] = useState(false);
  const [errorMessage, setErrorMessage] = useState("");
  const signOutUrl = "https://signin.aws.amazon.com/oauth?Action=logout";
  const localStorageRecentRolesKey = "consoleMeLocalStorage";
  const logOutIframeStyle = {
    width: 0,
    height: 0,
    border: "none",
  };

  const setRecentRoles = (role) => {
    let recentRoles = parseLocalStorageCache(localStorageRecentRolesKey);
    if (recentRoles == null) {
      recentRoles = [role];
    } else {
      const existingRoleLength = recentRoles.unshift(role);
      recentRoles = [...new Set(recentRoles)];
      if (existingRoleLength > 5) {
        recentRoles = recentRoles.slice(0, 5);
      }
    }
    window.localStorage.setItem(
      localStorageRecentRolesKey,
      JSON.stringify(recentRoles)
    );
  };

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
      setRecentRoles(roleData.role);
      setSignOut(true);
      setTimeout(() => {
        window.location.href = roleData.redirect_url;
      }, 2000);

      return;
    }

    if (roleData.type === "error") {
      setErrorMessage(roleData.message);
    }
  };

  loginAndRedirect();

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
