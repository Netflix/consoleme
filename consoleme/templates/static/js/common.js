async function sendRequestCommon(json, location = window.location.href) {
  let xsrf = await getCookie('_xsrf');
  const rawResponse = await fetch(location, {
    method: 'post',
    headers: {
      'Content-type': 'application/json',
      'X-Xsrftoken': xsrf,
    },
    body: json
  });

  let res = await rawResponse;

  let resJson;
  try {
    resJson = res.json();
  } catch (e) {
    resJson = res;
  }
  return await resJson;
}

async function getCookie(name) {
  let r = document.cookie.match('\\b' + name + '=([^;]*)\\b')
  return r ? r[1] : undefined
}

function formatRoleName(role, accounts) {
  // This will print the proper display name for the per-user roles.
  if (typeof role !== 'undefined') {
    if (!role.startsWith("cm-")) {
      return role;
    }
    return accounts[role.split("cm-")[1].split("-")[0]];
  } else {
    return role;
  }
}

async function handleResponse(res, redirect_uri = null, message = "Success! Refreshing cache and reloading the page.", delay = 0, htmlMessage = "") {
  document.getElementById('error_div').classList.add('hidden');
  document.getElementById('success_div').classList.add('hidden');
  console.log(res)
  if (res.status !== "success") {
    let element = document.getElementById('error_response');
    document.getElementById('error_div').classList.remove('hidden');
    if(res.hasOwnProperty("message")) {
      // since sometimes we return error message string and sometimes error message JSON object
      if(typeof res.message === "string") {
        element.textContent = res.message
      } else {
        element.textContent = JSON.stringify(res.message, null, '\t');
      }
    } else {
      element.textContent = JSON.stringify(res, null, '\t');
    }
    $('.ui.basic.modal').modal('show')
  } else {
    let element = document.getElementById('success_response');
    if(htmlMessage === "") {
      element.textContent = message;
    } else {
      element.innerHTML = htmlMessage;
    }
    document.getElementById('success_div').classList.remove('hidden')
    $('.ui.basic.modal').modal('show');
    setTimeout(() => {
      if (redirect_uri) {
        window.location.replace(redirect_uri);
      } else {
        location.reload();
      }
    }, delay )
  }
}

function restrictCharacters(myfield, e, restrictionType) {
  // Stolen from https://www.qodo.co.uk/blog/javascript-restrict-keyboard-character-input/
  if (!e) {
    e = window.event;
  }
  if (e.keyCode) code = e.keyCode;
  else if (e.which) code = e.which;
  let character = String.fromCharCode(code);
  // if they pressed esc... remove focus from field...
  if (code === 27) {
    this.blur();
    return false;
  }
  // ignore if they are press other keys
  // strange because code: 39 is the down key AND ' key...
  // and DEL also equals .
  if (!e.ctrlKey && code !== 9 && code !== 8 && code !== 36 && code !== 37 && code !== 38 && (code !== 39 || (code === 39 && character === "'")) && code !== 40) {
    return !!character.match(restrictionType);
  }
}