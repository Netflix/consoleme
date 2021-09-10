import React, { useEffect, useState } from "react";
import { useParams } from "react-router-dom";
import { useAuth } from "../../auth/AuthProviderDefault";
import { Button } from "semantic-ui-react";
import ReactMarkdown from "react-markdown";

const ConsoleMeChallengeValidator = () => {
  const { challengeToken } = useParams();
  const [result, setResult] = useState("");
  const [showApproveButton, setShowApproveButton] = useState(false);
  const { sendRequestCommon } = useAuth();

  useEffect(() => {
    (async () => {
      const res = await sendRequestCommon(
        null,
        "/api/v2/challenge_validator/" + challengeToken,
        "get"
      );
      if (!res) {
        return;
      }
      setResult(res);
      setShowApproveButton(res?.show_approve_button || false);
    })();
  }, [challengeToken, sendRequestCommon]);

  const validateChallengeToken = async () => {
    const res = await sendRequestCommon(
      { nonce: result?.nonce },
      "/api/v2/challenge_validator/" + challengeToken,
      "post"
    );
    if (!res) {
      return;
    }
    setResult(res);
    setShowApproveButton(false);
  };

  return (
    <>
      <ReactMarkdown linkTarget="_blank" children={result && result.message} />
      {showApproveButton ? (
        <Button primary type="submit" onClick={validateChallengeToken}>
          Approve Credential Request
        </Button>
      ) : null}
    </>
  );
};

export default ConsoleMeChallengeValidator;
