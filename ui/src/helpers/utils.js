const ALPHABET =
  "0123456789abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ";

export function random_id() {
  let rtn = "";
  for (let i = 0; i < 8; i++) {
    rtn += ALPHABET.charAt(Math.floor(Math.random() * ALPHABET.length));
  }
  return rtn;
}

export function generate_id() {
  return "ConsoleMe" + random_id();
}

export function generate_temp_id(expiration_date) {
  return "temp_" + expiration_date + "_" + random_id();
}

export async function getCookie(name) {
  const r = document.cookie.match("\\b" + name + "=([^;]*)\\b");
  return r ? r[1] : undefined;
}

async function processResponseAndMaybeAuth(rawResponse) {
  const response = await rawResponse;
  let resJson;
  try {
    resJson = await response.json();
    if (
      response.status === 403 &&
      resJson.type === "redirect" &&
      resJson.reason === "unauthenticated"
    ) {
      const auth = await fetch(
        "/auth?redirect_url=" + window.location.href
      ).then((res) => res.json());
      // redirect to IDP for authentication.
      if (auth.type === "redirect") {
        window.location.href = auth.redirect_url;
      }
    }
  } catch (e) {
    resJson = response;
  }
  return resJson;
}

export async function sendRequestCommon(
  json,
  location = window.location.href,
  method = "post"
) {
  const xsrf = await getCookie("_xsrf");
  let body = null;
  if (json) {
    body = JSON.stringify(json);
  }
  const rawResponse = await fetch(location, {
    method: method,
    headers: {
      "Content-type": "application/json",
      "X-Xsrftoken": xsrf,
    },
    body: body,
  });
  return await processResponseAndMaybeAuth(rawResponse);
}

export function PolicyTypeahead(value, callback, limit = 20) {
  const url =
    "/api/v2/typeahead/resources?typeahead=" + value + "&limit=" + limit;

  sendRequestCommon(null, url, "get").then((results) => {
    const matching_resources = [];
    results.forEach((result) => {
      // Strip out what the user has currently typed (`row`) from the full value returned from typeahead
      matching_resources.push({
        name: result,
        value: result,
        meta: "Resource",
        score: 1000,
      });
    });
    callback(null, matching_resources);
  });
}

export function getCompletions(editor, session, pos, prefix, callback) {
  let resource = false;
  let action = false;

  const lines = editor.getValue().split("\n");
  for (let i = pos.row; i >= 0; i--) {
    if (lines[i].indexOf('"Resource"') > -1) {
      resource = true;
      break;
    }

    if (lines[i].indexOf('"Action"') > -1) {
      action = true;
      break;
    }
  }
  // Only start typeahead if we have more than 3 characters to work with
  if (resource && prefix.length <= 3) {
    callback(null, []);
    return;
  }
  // Check for other statements? The beginning of the statement? The curly bracket?
  // if not action or resource do nothing?
  if (prefix.length === 0 || (action === false && resource === false)) {
    callback(null, []);
    return;
  }

  const row = session.getDocument().getLine(pos.row).trim().replace(/\"/g, "");
  if (action === true) {
    sendRequestCommon(
      null,
      "/api/v1/policyuniverse/autocomplete?prefix=" + row,
      "get"
    ).then((wordList) => {
      // wordList like [{"permission":"s3:GetObject"}]
      callback(
        null,
        wordList.map((ea) => {
          let value = ea.permission;
          if (row.indexOf(":") > -1) {
            value = value.split(":")[1];
          }
          return {
            name: ea.permission,
            value,
            meta: "Permission",
            score: 1000,
          };
        })
      );
    });
  } else if (resource === true) {
    // We know we're in the Resource section, so let's help type the ARN
    new PolicyTypeahead(row, callback, 500000);
  }
}

export async function getMonacoCompletions(model, position, monaco) {
  let resource = false;
  let action = false;

  const lines = model.getLinesContent();

  for (let i = position.lineNumber - 1; i >= 0; i--) {
    if (lines[i].indexOf('"Resource"') > -1) {
      resource = true;
      break;
    }

    if (lines[i].indexOf('"Action"') > -1) {
      action = true;
      break;
    }

    if (lines[i].indexOf('"Sid"') > -1) {
      return { suggestions: [] };
    }
  }
  const lastLine = model.getLineContent(position.lineNumber);
  const prefix = lastLine
    .trim()
    .replace(/"/g, "")
    .replace(/Action:/g, "")
    .replace(/Resource:/g, "")
    .replace(/,/g, "")
    .replace(" ", "")
    .replace(/\[/, "")
    .replace(/]/, "");
  // prefixRange is the range of the prefix that will be replaced if someone selects the suggestion
  const prefixRange = model.findPreviousMatch(prefix, position);
  const defaultWordList = [];
  if (action === true) {
    const wordList = await sendRequestCommon(
      null,
      "/api/v1/policyuniverse/autocomplete?prefix=" + prefix,
      "get"
    );
    if (!prefixRange) {
      return { suggestions: defaultWordList };
    }
    const suggestedWordList = wordList.map((ea) => ({
      label: ea.permission,
      insertText: ea.permission,
      kind: monaco.languages.CompletionItemKind.Property,
      range: prefixRange.range,
    }));
    return { suggestions: suggestedWordList };
    // TODO: error handling other than returning empty list ?
  } else if (resource === true) {
    const wordList = await sendRequestCommon(
      null,
      "/api/v2/typeahead/resources?typeahead=" + prefix,
      "get"
    );
    const suggestedWordList = wordList.map((ea) => ({
      label: ea,
      insertText: ea,
      kind: monaco.languages.CompletionItemKind.Function,
      range: prefixRange.range,
    }));
    return { suggestions: suggestedWordList };
    // TODO: error handling other than returning empty list ?
  }
  return { suggestions: defaultWordList };
}

export function getMonacoTriggerCharacters() {
  const lowerCase = "abcdefghijklmnopqrstuvwxyz";
  return (lowerCase + lowerCase.toUpperCase() + "0123456789" + "_-:").split("");
}

export function sortAndStringifyNestedJSONObject(input = {}) {
  const allOldKeys = [];
  JSON.stringify(input, (key, value) => {
    allOldKeys.push(key);
    return value;
  });
  return JSON.stringify(input, allOldKeys.sort(), 4);
}

export function updateRequestStatus(command) {
  const { requestID } = this.state;
  this.setState(
    {
      isLoading: true,
    },
    async () => {
      const request = {
        modification_model: {
          command,
        },
      };
      await sendRequestCommon(
        request,
        "/api/v2/requests/" + requestID,
        "PUT"
      ).then((response) => {
        if (
          response.status === 403 ||
          response.status === 400 ||
          response.status === 500
        ) {
          // Error occurred making the request
          this.setState({
            isLoading: false,
            buttonResponseMessage: [
              {
                status: "error",
                message: response.message,
              },
            ],
          });
        } else {
          // Successful request
          this.setState({
            isLoading: false,
            buttonResponseMessage: response.action_results.reduce(
              (resultsReduced, result) => {
                if (result.visible === true) {
                  resultsReduced.push(result);
                }
                return resultsReduced;
              },
              []
            ),
          });
          this.reloadDataFromBackend();
        }
      });
    }
  );
}

export async function sendProposedPolicyWithHooks(
  command,
  change,
  newStatement,
  requestID,
  setIsLoading,
  setButtonResponseMessage,
  reloadDataFromBackend
) {
  setIsLoading(true);
  const request = {
    modification_model: {
      command,
      change_id: change.id,
    },
  };
  if (newStatement) {
    request.modification_model.policy_document = JSON.parse(newStatement);
  }
  await sendRequestCommon(request, "/api/v2/requests/" + requestID, "PUT").then(
    (response) => {
      if (
        response.status === 403 ||
        response.status === 400 ||
        response.status === 500
      ) {
        // Error occurred making the request
        setIsLoading(false);
        setButtonResponseMessage([
          {
            status: "error",
            message: response.message,
          },
        ]);
      } else {
        // Successful request
        setIsLoading(false);
        setButtonResponseMessage(
          response.action_results.reduce((resultsReduced, result) => {
            if (result.visible === true) {
              resultsReduced.push(result);
            }
            return resultsReduced;
          }, [])
        );
        reloadDataFromBackend();
      }
    }
  );
}

export function sendProposedPolicy(command) {
  const { change, newStatement, requestID } = this.state;
  this.setState(
    {
      isLoading: true,
    },
    async () => {
      const request = {
        modification_model: {
          command,
          change_id: change.id,
        },
      };
      if (newStatement) {
        request.modification_model.policy_document = JSON.parse(newStatement);
      }
      await sendRequestCommon(
        request,
        "/api/v2/requests/" + requestID,
        "PUT"
      ).then((response) => {
        if (
          response.status === 403 ||
          response.status === 400 ||
          response.status === 500
        ) {
          // Error occurred making the request
          this.setState({
            isLoading: false,
            buttonResponseMessage: [
              {
                status: "error",
                message: response.message,
              },
            ],
          });
        } else {
          // Successful request
          this.setState({
            isLoading: false,
            buttonResponseMessage: response.action_results.reduce(
              (resultsReduced, result) => {
                if (result.visible === true) {
                  resultsReduced.push(result);
                }
                return resultsReduced;
              },
              []
            ),
          });
          this.reloadDataFromBackend();
        }
      });
    }
  );
}
