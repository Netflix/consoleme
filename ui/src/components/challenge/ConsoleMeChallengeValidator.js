import React, { useEffect, useState } from "react";
import { sendRequestCommon } from "../../helpers/utils";
import { useParams } from "react-router-dom";

const ConsoleMeChallengeValidator = () => {
  const { challengeToken } = useParams();
  const [result, setResult] = useState("");
  useEffect(() => {
    async function validateChallenge() {
      setResult(
        await sendRequestCommon(
          null,
          "/api/v2/challenge_validator/" + challengeToken,
          "get"
        )
      );
    }
    validateChallenge();
  }, []);

  return <p>{result && result.message}</p>;
};

export default ConsoleMeChallengeValidator;
