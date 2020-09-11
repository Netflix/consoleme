async function updateDynamicConfig(editor_value) {
  let lint_errors = editor_value.getSession().getAnnotations();
  if (lint_errors.length > 0) {
    alert("Lint Error: " + JSON.stringify(lint_errors));
    return false;
  }

  let arr = { new_config: eval(editor_value).getValue() };
  let json = JSON.stringify(arr);
  let dimmer = $(".ui.dimmer");
  dimmer.addClass("active");
  let res = await sendRequestCommon(json);
  dimmer.removeClass("active");
  await handleResponse(res);
}
