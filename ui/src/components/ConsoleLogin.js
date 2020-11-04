import React, {ComponentType} from "react"
import {sendRequestCommon} from "../helpers/utils";
import {useParams} from "react-router-dom";
import qs from "qs";

function ConsoleLogin(props) {
  const {roleQuery} = useParams();
  const queryString = window.location.search;
  console.log(queryString)
  console.log(roleQuery)
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
      {
        limit: 1000,
      },
      "/",
      "get"
    );
    console.log(roleData)
    const parsedQueryString = qs.parse(queryString, {
      ignoreQueryPrefix: true,
    });

    console.log(parsedQueryString)

  }

  const logOutIframe = () => {
    const logOutIframeStyle = {
      width: 0,
      height: 0,
      border: "none"
    }
    return <iframe title={"logOutIframe"} style={logOutIframeStyle}/>
  }

  const result = loginAndRedirect()

  return (
    <>
      LOL
      {logOutIframe()}
    </>
  )
}


export default ConsoleLogin;