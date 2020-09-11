function getCookie(name) {
  let r = document.cookie.match("\\b" + name + "=([^;]*)\\b");
  return r ? r[1] : undefined;
}

function sendRequest(json, endpoint) {
  let XHR = new XMLHttpRequest();
  let xsrf = getCookie("_xsrf");
  let req = JSON.parse(json)

  XHR.addEventListener("load", function (event) {
    try {
      let res = JSON.parse(event.target.responseText);
    } catch (err) {
      console.log(err)
      res = {}
    }
    if (res.status == "error") {
      let element = document.getElementById("error_response");
      element.textContent = res.message;
      document.getElementById("error_div").classList.remove("hidden");
    } else if (res.status == "success") {
      let element = document.getElementById("success_response");
      element.textContent = res.message;
      document.getElementById("success_div").classList.remove("hidden");

    } else {
      let element = document.getElementById("error_response");
      element.textContent = event.target.responseText;
      document.getElementById("error_div").classList.remove("hidden");
    }
  });

  XHR.addEventListener("error", function (event) {
    alert('Oops! Something went wrong.');
  });

  // Set up our request
  XHR.open("POST", endpoint);
  XHR.setRequestHeader("X-Xsrftoken", xsrf);

  XHR.send(json);
}

async function removeUser (user) {
  document.getElementById('error_div').classList.add('hidden');
  document.getElementById('success_div').classList.add('hidden');
  let arr = [{"name": "remove_groups", "value": user}];
  let json = JSON.stringify(arr);
  $('.ui.dimmer').addClass('active');
  let res = await sendRequestCommon(json);
  $('.ui.dimmer').removeClass('active');
  let element = null;
  if (res.status === 'error') {
    element = document.getElementById('error_response');
    element.textContent = res.message;
    document.getElementById('error_div').classList.remove('hidden')
  } else if (res.status === 'success') {
    element = document.getElementById('success_response');
    element.textContent = res.message;
    document.getElementById('success_div').classList.remove('hidden')
  } else {
    element = document.getElementById('error_response');
    element.textContent = event.target.responseText;
    document.getElementById('error_div').classList.remove('hidden')
  }

  element = document.getElementById('modal_content');
  element.innerHTML = res.html
  $('.ui.basic.modal')
    .modal('show')
}
