import React, { useEffect, useState } from "react";
import { sendRequestCommon } from "../../helpers/utils";
import { useParams } from "react-router-dom";

const ConsoleMeChallengeValidator = () => {
  const { challengeToken } = useParams();
  const [result, setResult] = useState("");
  useEffect(() => {
    (async () => {
      setResult(
        await sendRequestCommon(
          null,
          "/api/v2/challenge_validator/" + challengeToken,
          "get"
        )
      );
    })();
  }, [challengeToken]);

  return <p>{result && result.message}</p>;
};

export default ConsoleMeChallengeValidator;
