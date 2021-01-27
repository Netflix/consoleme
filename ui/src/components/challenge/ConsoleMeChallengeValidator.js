import React, { useEffect, useState } from "react";
import { useParams } from "react-router-dom";
import { useAuth } from "../../auth/AuthProviderDefault";

const ConsoleMeChallengeValidator = () => {
  const { challengeToken } = useParams();
  const [result, setResult] = useState("");
  const { sendRequestCommon } = useAuth();

  useEffect(() => {
    (async () => {
      const result = await sendRequestCommon(
        null,
        "/api/v2/challenge_validator/" + challengeToken,
        "get"
      );
      if (!result) {
        return;
      }
      setResult(result);
    })();
  }, [challengeToken, sendRequestCommon]);

  return <p>{result && result.message}</p>;
};

export default ConsoleMeChallengeValidator;
