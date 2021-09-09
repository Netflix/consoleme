import YAML from "yaml";

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

export function getCookie(name) {
  const r = document.cookie.match("\\b" + name + "=([^;]*)\\b");
  return r ? r[1] : undefined;
}

// NOTE: avoid using sendRequestCommon from utils file.
async function sendRequestCommon(
  json,
  location = window.location.href,
  method = "post"
) {
  const xsrf = getCookie("_xsrf");
  let body = null;
  if (json) {
    body = JSON.stringify(json);
  }
  const rawResponse = await fetch(location, {
    method: method,
    headers: {
      "Content-type": "application/json",
      "X-Xsrftoken": xsrf,
      "X-Requested-With": "XMLHttpRequest",
      Accept: "application/json",
    },
    body: body,
  });
  const response = await rawResponse;

  let resJson;
  try {
    resJson = await response.json();
    if (
      response.status === 403 &&
      resJson.type === "redirect" &&
      resJson.reason === "unauthenticated"
    ) {
      const auth = await fetch("/auth?redirect_url=" + window.location.href, {
        headers: {
          "X-Requested-With": "XMLHttpRequest",
          Accept: "application/json",
        },
      }).then((res) => res.json());
      // redirect to IDP for authentication.
      if (auth.type === "redirect") {
        window.location.href = auth.redirect_url;
      }
    } else if (response.status === 401) {
      return null;
    }
  } catch (e) {
    resJson = response;
  }

  return resJson;
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

    if (!wordList) {
      return { suggestions: defaultWordList };
    }

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

    if (!wordList) {
      return { suggestions: defaultWordList };
    }

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
      case "iamuser": {
        return `/api/v2/users/${accountID}/${resourceName}`;
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
      case "managed_policy": {
        return `/api/v2/resources/${accountID}/managed_policy/${resourceName}`;
      }
      default: {
        throw new Error("No such service exist");
      }
    }
  })(accountID, serviceType, region, resourceName);

  return endpoint;
};

export const parseLocalStorageCache = (key, default_return = []) => {
  const value = window.localStorage.getItem(key);
  if (value == null) {
    return default_return;
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

export function getStringFormat(str) {
  try {
    JSON.parse(str);
    return "json";
  } catch (e) {}
  try {
    YAML.parse(str);
    return "yaml";
  } catch (e) {}
  return "plaintext";
}

export const delay = (ms) => new Promise((resolve) => setTimeout(resolve, ms));

// Editor theme support

export const editor_themes = [
  {
    key: "vs-light",
    text: "vs-light",
    value: "vs-light",
  },
  {
    key: "vs-dark",
    text: "vs-dark",
    value: "vs-dark",
  },
  {
    key: "hc-black",
    text: "hc-black",
    value: "hc-black",
  },
];

const default_user_settings = {
  editorTheme: "vs-light",
};

export const getLocalStorageSettings = (specificSetting = "") => {
  const localStorageSettingsKey = "consoleMeUserSettings";
  let localSettings = parseLocalStorageCache(
    localStorageSettingsKey,
    default_user_settings
  );
  if (specificSetting === "") {
    return localSettings;
  }
  if (localSettings.hasOwnProperty(specificSetting)) {
    return localSettings[specificSetting];
  }
  return "";
};

export const setLocalStorageSettings = (settings) => {
  const localStorageSettingsKey = "consoleMeUserSettings";
  window.localStorage.setItem(
    localStorageSettingsKey,
    JSON.stringify(settings)
  );
};

export const arnRegex = /^arn:aws:iam::(?<accountId>\d{12}):(?<resourceType>(user|role))\/(.+\/)?(?<resourceName>(.+))/;
