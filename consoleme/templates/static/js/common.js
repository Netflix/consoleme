Array.prototype.unique = function () {
  return this.filter((value, index, self) => self.indexOf(value) === index);
};

async function sendRequestCommon(json, location = window.location.href) {
  const xsrf = await getCookie("_xsrf");
  const rawResponse = await fetch(location, {
    method: "post",
    headers: {
      "Content-type": "application/json",
      "X-Xsrftoken": xsrf,
    },
    body: json,
  });

  const res = await rawResponse;

  let resJson;
  try {
    resJson = res.json();
  } catch (e) {
    resJson = res;
  }
  return await resJson;
}

async function getCookie(name) {
  const r = document.cookie.match("\\b" + name + "=([^;]*)\\b");
  return r ? r[1] : undefined;
}

function formatRoleName(role, accounts) {
  // This will print the proper display name for the per-user roles.
  if (typeof role !== "undefined") {
    if (!role.startsWith("cm-")) {
      return role;
    }
    return accounts[role.split("cm-")[1].split("-")[0]];
  }
  return role;
}

async function handleResponse(
  res,
  redirect_uri = null,
  message = "Success! Refreshing cache and reloading the page.",
  delay = 0,
  htmlMessage = ""
) {
  document.getElementById("error_div").classList.add("hidden");
  document.getElementById("success_div").classList.add("hidden");
  if (res.status !== "success") {
    const element = document.getElementById("error_response");
    document.getElementById("error_div").classList.remove("hidden");
    if (res.hasOwnProperty("message")) {
      // since sometimes we return error message string and sometimes error message JSON object
      if (typeof res.message === "string") {
        element.textContent = res.message;
      } else {
        element.textContent = JSON.stringify(res.message, null, "\t");
      }
    } else {
      element.textContent = JSON.stringify(res, null, "\t");
    }
    $(".ui.basic.modal").modal("show");
  } else {
    const element = document.getElementById("success_response");
    if (htmlMessage === "") {
      element.textContent = message;
    } else {
      element.innerHTML = htmlMessage;
    }
    document.getElementById("success_div").classList.remove("hidden");
    $(".ui.basic.modal").modal("show");
    setTimeout(() => {
      if (redirect_uri) {
        window.location.replace(redirect_uri);
      } else {
        location.reload();
      }
    }, delay);
  }
}

function restrictCharacters(myfield, e, restrictionType) {
  // Stolen from https://www.qodo.co.uk/blog/javascript-restrict-keyboard-character-input/
  if (!e) {
    e = window.event;
  }
  if (e.keyCode) code = e.keyCode;
  else if (e.which) code = e.which;
  const character = String.fromCharCode(code);
  // if they pressed esc... remove focus from field...
  if (code === 27) {
    this.blur();
    return false;
  }
  // ignore if they are press other keys
  // strange because code: 39 is the down key AND ' key...
  // and DEL also equals .
  if (
    !e.ctrlKey &&
    code !== 9 &&
    code !== 8 &&
    code !== 36 &&
    code !== 37 &&
    code !== 38 &&
    (code !== 39 || (code === 39 && character === "'")) &&
    code !== 40
  ) {
    return !!character.match(restrictionType);
  }
}

function parseLocalStorageCache() {
  key = "consoleMeLocalStorage";
  if (typeof Storage === "undefined") {
    return null;
  }
  stored_values = localStorage.getItem(key);
  if (stored_values == null) {
    return null;
  }
  return JSON.parse(stored_values);
}

function reset_options() {
  $("#account").val("").trigger("chosen:updated");
}

function setLocalStorageCache(role) {
  key = "consoleMeLocalStorage";
  roles = parseLocalStorageCache();
  // We don't use "Set()" because we want the last selected role to be on top of the recent roles list
  if (roles == null) {
    roles = [];
    roles[0] = role;
  } else {
    const uniqueRoles = [];
    len = roles.unshift(role);
    roles = roles.unique();
    if (len > 5) {
      roles = roles.slice(0, 5);
    }
  }
  localStorage.setItem(key, JSON.stringify(roles));
}

function log(message, debug = false) {
  if (debug) {
    console.log(message);
  }
}

function log_completion() {
  log("Request completed.");
}

function getDebugLoggingKey() {
  key = "consoleMeDebugLogging";

  if (typeof Storage === "undefined") {
    return null;
  }

  stored_values = localStorage.getItem(key);
  if (stored_values == null) {
    return null;
  }

  return true;
}

function setRecentRole(field) {
  const radios = document.getElementsByName(field);
  for (let i = 0, length = radios.length; i < length; i++) {
    if (radios[i].checked) {
      return setLocalStorageCache(radios[i].value);
    }
  }
}
