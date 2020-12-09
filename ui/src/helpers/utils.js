import { sendRequestTarget } from "../auth/AuthProviderDefault";

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

export async function sendRequestCommon(
  json,
  location = window.location.href,
  method = "post"
) {
  const xsrf = await getCookie("_xsrf");
  return await sendRequestTarget(json, location, method, xsrf);
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

  const row = session.getDocument().getLine(pos.row).trim().replace(/"/g, "");
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
  return (lowerCase + lowerCase.toUpperCase() + "0123456789_-:").split("");
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

export const getResourceEndpoint = (
  accountID,
  serviceType,
  region,
  resourceName
) => {
  const endpoint = ((accountID, serviceType, region, resourceName) => {
    switch (serviceType) {
      case "iamrole": {
        return `/api/v2/roles/${accountID}/${resourceName}`;
      }
      case "s3": {
        return `/api/v2/resources/${accountID}/s3/${resourceName}`;
      }
      case "sqs": {
        return `/api/v2/resources/${accountID}/sqs/${region}/${resourceName}`;
      }
      case "sns": {
        return `/api/v2/resources/${accountID}/sns/${region}/${resourceName}`;
      }
      default: {
        throw new Error("No such service exist");
      }
    }
  })(accountID, serviceType, region, resourceName);

  return endpoint;
};

export const sendRequestV2 = async (requestV2) => {
  const response = await sendRequestCommon(requestV2, "/api/v2/request");

  if (response) {
    const { request_created, request_id, request_url, errors } = response;
    if (request_created === true) {
      if (requestV2.admin_auto_approve && errors === 0) {
        return {
          message: `Successfully created and applied request: [${request_id}](${request_url}).`,
          request_created,
          error: false,
        };
      } else if (errors === 0) {
        return {
          message: `Successfully created request: [${request_id}](${request_url}).`,
          request_created,
          error: false,
        };
      } else {
        return {
          // eslint-disable-next-line max-len
          message: `This request was created and partially successful: : [${request_id}](${request_url}). But the server reported some errors with the request: ${JSON.stringify(
            response
          )}`,
          request_created,
          error: true,
        };
      }
    }
    return {
      message: `Server reported an error with the request: ${JSON.stringify(
        response
      )}`,
      request_created,
      error: true,
    };
  } else {
    return {
      message: `"Failed to submit request: ${JSON.stringify(response)}`,
      request_created: false,
      error: true,
    };
  }
};

export const parseLocalStorageCache = (key) => {
  const value = window.localStorage.getItem(key);
  if (value == null) {
    return [];
  }
  try {
    return JSON.parse(value);
  } catch {
    return value;
  }
};

export const setRecentRoles = (role) => {
  const localStorageRecentRolesKey = "consoleMeLocalStorage";
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

export const delay = (ms) => new Promise((resolve) => setTimeout(resolve, ms));
